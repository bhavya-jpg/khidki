"""Khidki on AWS (ap-southeast-2, the account's home region).

DynamoDB (single table) · Lambda (api, ingest, planner, nudge_task) · API Gateway HTTP API · Step Functions
NudgeSM (task-token callback, wait, verify from CO₂) · EventBridge Scheduler (06:00 Asia/Kolkata) · S3 (Polly
audio cache) · SSM (device and admin keys) · Amplify Hosting (web, /v1 proxied to the API) · CloudWatch
(dashboard + alarms) · SNS (alarm emails) · AWS Budgets (an email at the first cent).

Cost rule: stay inside the always-free allowances. No always-on compute, no point-in-time recovery, the
public API is throttled, and a 1 USD budget emails the owner as soon as any spend shows up.
"""

from __future__ import annotations

from pathlib import Path

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_amplify as amplify
from aws_cdk import aws_apigatewayv2 as apigw
from aws_cdk import aws_apigatewayv2_integrations as integ
from aws_cdk import aws_budgets as budgets
from aws_cdk import aws_cloudwatch as cw
from aws_cdk import aws_cloudwatch_actions as cw_actions
from aws_cdk import aws_dynamodb as ddb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_scheduler as scheduler
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as subs
from aws_cdk import aws_ssm as ssm
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as tasks
from constructs import Construct

ROOT = Path(__file__).resolve().parents[2]
SM_NAME = "Khidki-NudgeSM"


class KhidkiStack(Stack):
    def __init__(
        self,
        scope: Construct,
        cid: str,
        *,
        device_key: str,
        admin_key: str,
        alert_email: str = "",
        **kwargs: object,
    ) -> None:
        super().__init__(scope, cid, **kwargs)  # type: ignore[arg-type]

        table = ddb.Table(
            self,
            "Table",
            table_name="Khidki",
            partition_key=ddb.Attribute(name="pk", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="sk", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="ttl",
            # No point-in-time recovery: it is billed per GB and this is replayable demo data.
            removal_policy=RemovalPolicy.DESTROY,
        )
        bucket = s3.Bucket(
            self,
            "Assets",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )
        device_param = ssm.StringParameter(
            self,
            "DeviceKey",
            parameter_name="/khidki/device_key",
            string_value=device_key,
            description="Demo sensor/simulator key",
        )
        admin_param = ssm.StringParameter(
            self,
            "AdminKey",
            parameter_name="/khidki/admin_key",
            string_value=admin_key,
            description="Demo admin passcode",
        )

        layer = lambda_.LayerVersion(
            self,
            "Deps",
            code=lambda_.Code.from_asset(str(ROOT / "build" / "layer")),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            compatible_architectures=[lambda_.Architecture.X86_64],
            description="numpy, pydantic, cedarpy, Powertools",
        )
        code = lambda_.Code.from_asset(str(ROOT / "build" / "lambda"))
        sm_arn = f"arn:aws:states:{self.region}:{self.account}:stateMachine:{SM_NAME}"
        env = {
            "KHIDKI_TABLE": table.table_name,
            "KHIDKI_BUCKET": bucket.bucket_name,
            "KHIDKI_NUDGE_SM": sm_arn,
            "KHIDKI_ORIGINS": "http://localhost:5173",
            "POWERTOOLS_SERVICE_NAME": "khidki",
            "POWERTOOLS_METRICS_NAMESPACE": "Khidki",
        }

        def fn(name: str, handler: str, memory: int, timeout_s: int) -> lambda_.Function:
            f = lambda_.Function(
                self,
                name,
                function_name=f"khidki-{name.lower()}",
                runtime=lambda_.Runtime.PYTHON_3_12,
                architecture=lambda_.Architecture.X86_64,
                handler=f"khidki_cloud.handlers.{handler}",
                code=code,
                layers=[layer],
                memory_size=memory,
                timeout=Duration.seconds(timeout_s),
                environment=env,
                tracing=lambda_.Tracing.ACTIVE,
                log_group=logs.LogGroup(
                    self,
                    f"{name}Logs",
                    log_group_name=f"/aws/lambda/khidki-{name.lower()}",
                    retention=logs.RetentionDays.TWO_WEEKS,
                    removal_policy=RemovalPolicy.DESTROY,
                ),
            )
            table.grant_read_write_data(f)
            device_param.grant_read(f)
            admin_param.grant_read(f)
            # Start NudgeSM and hand taps back to it. The ARN is built from the fixed name, so there is no
            # dependency cycle between the state machine and the functions it calls.
            f.add_to_role_policy(iam.PolicyStatement(actions=["states:StartExecution"], resources=[sm_arn]))
            f.add_to_role_policy(
                iam.PolicyStatement(
                    actions=["states:SendTaskSuccess", "states:SendTaskFailure", "states:SendTaskHeartbeat"],
                    resources=[sm_arn],
                )
            )
            return f

        api_fn = fn("Api", "api", 1769, 29)
        ingest_fn = fn("Ingest", "ingest", 1769, 29)
        planner_fn = fn("Planner", "planner", 1769, 120)
        nudge_fn = fn("NudgeTask", "nudge_task", 1024, 60)
        bucket.grant_read_write(api_fn)
        api_fn.add_to_role_policy(iam.PolicyStatement(actions=["polly:SynthesizeSpeech"], resources=["*"]))
        for f in (api_fn,):
            f.add_to_role_policy(
                iam.PolicyStatement(
                    actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                    resources=[
                        "arn:aws:bedrock:*::foundation-model/amazon.nova-*",
                        f"arn:aws:bedrock:*:{self.account}:inference-profile/*",
                    ],
                )
            )

        # ── NudgeSM ─────────────────────────────────────────────────────────────────────────────────
        def await_tap(name: str) -> tasks.LambdaInvoke:
            return tasks.LambdaInvoke(
                self,
                name,
                lambda_function=nudge_fn,
                integration_pattern=sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
                payload=sfn.TaskInput.from_object(
                    {
                        "mode": "await_ack",
                        "nudge_id": sfn.JsonPath.string_at("$.nudge_id"),
                        "token": sfn.JsonPath.task_token,
                    }
                ),
                task_timeout=sfn.Timeout.at("$.ack_timeout_s"),
                result_path="$.ack",
                comment="Show the instruction and wait for the teacher's tap (callback with a task token)",
            )

        def step(name: str, mode: str, result_path: str, comment: str) -> tasks.LambdaInvoke:
            return tasks.LambdaInvoke(
                self,
                name,
                lambda_function=nudge_fn,
                payload_response_only=True,
                result_path=result_path,
                payload=sfn.TaskInput.from_object(
                    {"mode": mode, "nudge_id": sfn.JsonPath.string_at("$.nudge_id")}
                ),
                comment=comment,
            )

        issue = await_tap("IssueNudge")
        follow_up = await_tap("FollowUpNudge")
        timed_out = step("NoTapInTime", "timeout", "$.t", "Nobody tapped: verify from the air anyway")
        wait = sfn.Wait(
            self,
            "WaitThenVerify",
            time=sfn.WaitTime.seconds_path("$.verify_wait_s"),
            comment="Give the air 3 simulated minutes to change",
        )
        verify = step("VerifyFromCO2", "verify", "$.v", "Fit the air-change rate to the CO₂ curve")
        verified = sfn.Succeed(self, "Verified", comment="The air really changed")
        not_followed = sfn.Succeed(
            self, "NotFollowed_Replanned", comment="Re-planned from the measured state"
        )
        not_possible = sfn.Succeed(self, "CantRightNow_Replanned", comment="Constraint recorded, re-planned")

        tapped = (
            sfn.Choice(self, "TeacherTapped")
            .when(sfn.Condition.string_equals("$.ack.result", "cant"), not_possible)
            .otherwise(wait)
        )
        outcome = (
            sfn.Choice(self, "AirChanged")
            .when(sfn.Condition.string_equals("$.v.status", "follow_up"), follow_up)
            .when(
                sfn.Condition.or_(
                    sfn.Condition.string_equals("$.v.outcome", "verified"),
                    sfn.Condition.string_equals("$.v.outcome", "verified_silent"),
                ),
                verified,
            )
            .otherwise(not_followed)
        )
        issue.add_catch(timed_out, errors=["States.Timeout"], result_path="$.timeout")
        follow_up.add_catch(timed_out, errors=["States.Timeout"], result_path="$.timeout")
        issue.next(tapped)
        follow_up.next(tapped)
        timed_out.next(wait)
        wait.next(verify)
        verify.next(outcome)
        sm = sfn.StateMachine(
            self,
            "NudgeSM",
            state_machine_name=SM_NAME,
            definition_body=sfn.DefinitionBody.from_chainable(issue),
            timeout=Duration.hours(2),
            tracing_enabled=True,
            logs=sfn.LogOptions(
                destination=logs.LogGroup(
                    self,
                    "NudgeSMLogs",
                    retention=logs.RetentionDays.TWO_WEEKS,
                    removal_policy=RemovalPolicy.DESTROY,
                ),
                level=sfn.LogLevel.ERROR,
            ),
        )

        # ── API ─────────────────────────────────────────────────────────────────────────────────────
        http = apigw.HttpApi(
            self,
            "Http",
            api_name="khidki",
            cors_preflight=apigw.CorsPreflightOptions(
                allow_origins=["http://localhost:5173"],
                allow_methods=[apigw.CorsHttpMethod.ANY],
                allow_headers=["content-type", "x-khidki-admin"],
            ),
        )
        http.add_routes(
            path="/v1/{proxy+}",
            methods=[apigw.HttpMethod.ANY],
            integration=integ.HttpLambdaIntegration("ApiInt", api_fn),
        )
        http.add_routes(
            path="/v1/ingest",
            methods=[apigw.HttpMethod.POST],
            integration=integ.HttpLambdaIntegration("IngestInt", ingest_fn),
        )
        # Three POST routes are open for the demo (tap, re-plan, ask). Throttle the whole stage so nobody can
        # run up calls: two tablets, the principal page and the simulator together stay under 5 requests/s.
        stage = http.default_stage.node.default_child if http.default_stage else None
        if isinstance(stage, apigw.CfnStage):
            stage.default_route_settings = apigw.CfnStage.RouteSettingsProperty(
                throttling_rate_limit=10, throttling_burst_limit=20
            )

        # ── 06:00 plan ──────────────────────────────────────────────────────────────────────────────
        sched_role = iam.Role(
            self, "SchedulerRole", assumed_by=iam.ServicePrincipal("scheduler.amazonaws.com")
        )
        planner_fn.grant_invoke(sched_role)
        scheduler.CfnSchedule(
            self,
            "MorningPlan",
            name="khidki-morning-plan",
            description="Plan every classroom's day at 06:00 IST",
            flexible_time_window=scheduler.CfnSchedule.FlexibleTimeWindowProperty(mode="OFF"),
            schedule_expression="cron(0 6 * * ? *)",
            schedule_expression_timezone="Asia/Kolkata",
            target=scheduler.CfnSchedule.TargetProperty(
                arn=planner_fn.function_arn, role_arn=sched_role.role_arn
            ),
        )

        # ── web ─────────────────────────────────────────────────────────────────────────────────────
        api_base = http.api_endpoint
        web = amplify.CfnApp(
            self,
            "Web",
            name="khidki",
            platform="WEB",
            custom_rules=[
                amplify.CfnApp.CustomRuleProperty(
                    source="/v1/<*>", target=f"{api_base}/v1/<*>", status="200"
                ),
                amplify.CfnApp.CustomRuleProperty(
                    source="</^[^.]+$|\\.(?!(css|gif|ico|jpg|jpeg|js|png|txt|svg|woff|woff2|ttf|map|json|mp3|webp)$)([^.]+$)/>",
                    target="/index.html",
                    status="200",
                ),
            ],
        )
        branch = amplify.CfnBranch(
            self, "WebMain", app_id=web.attr_app_id, branch_name="main", stage="PRODUCTION"
        )

        # ── observability ───────────────────────────────────────────────────────────────────────────
        def m(name: str, label: str) -> cw.Metric:
            return cw.Metric(
                namespace="Khidki",
                metric_name=name,
                dimensions_map={"service": "khidki"},
                statistic="Sum",
                period=Duration.minutes(1),
                label=label,
            )

        dash = cw.Dashboard(self, "Dashboard", dashboard_name="Khidki")
        dash.add_widgets(
            cw.GraphWidget(
                title="Nudges",
                width=12,
                left=[
                    m("NudgesIssued", "Issued"),
                    m("NudgesVerified", "Verified from CO₂"),
                    m("NudgesFollowUp", "Follow-ups"),
                    m("NudgesPartial", "Partial"),
                    m("NudgesNotFollowed", "Not followed"),
                    m("NudgesNotPossible", "Can't"),
                ],
            ),
            cw.GraphWidget(title="Readings ingested", width=12, left=[m("ReadingsIngested", "Readings")]),
        )
        dash.add_widgets(
            cw.GraphWidget(
                title="NudgeSM executions",
                width=12,
                left=[
                    sm.metric_started(period=Duration.minutes(1)),
                    sm.metric_succeeded(period=Duration.minutes(1)),
                    sm.metric_failed(period=Duration.minutes(1)),
                ],
            ),
            cw.GraphWidget(
                title="Lambda errors",
                width=12,
                left=[
                    f.metric_errors(period=Duration.minutes(1))
                    for f in (api_fn, ingest_fn, planner_fn, nudge_fn)
                ],
            ),
        )
        alarms = [
            cw.Alarm(
                self,
                f"{f.node.id}Errors",
                metric=f.metric_errors(period=Duration.minutes(5)),
                threshold=1,
                evaluation_periods=1,
                alarm_description=f"{f.node.id} Lambda errors",
            )
            for f in (api_fn, ingest_fn, nudge_fn)
        ]
        alarms.append(
            cw.Alarm(
                self,
                "NudgeSMFailed",
                metric=sm.metric_failed(period=Duration.minutes(5)),
                threshold=1,
                evaluation_periods=1,
                alarm_description="NudgeSM executions failed",
            )
        )

        # ── Alerts and the spend guard (only when an owner email is configured) ─────────────────────────
        if alert_email:
            topic = sns.Topic(self, "Alerts", display_name="Khidki alerts")
            topic.add_subscription(subs.EmailSubscription(alert_email))
            for alarm in alarms:
                alarm.add_alarm_action(cw_actions.SnsAction(topic))

            def notify(kind: str, percent: float) -> budgets.CfnBudget.NotificationWithSubscribersProperty:
                return budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        comparison_operator="GREATER_THAN",
                        notification_type=kind,
                        threshold=percent,
                        threshold_type="PERCENTAGE",
                    ),
                    subscribers=[
                        budgets.CfnBudget.SubscriberProperty(address=alert_email, subscription_type="EMAIL")
                    ],
                )

            budgets.CfnBudget(
                self,
                "SpendGuard",
                budget=budgets.CfnBudget.BudgetDataProperty(
                    budget_name="khidki-spend-guard",
                    budget_type="COST",
                    time_unit="MONTHLY",
                    budget_limit=budgets.CfnBudget.SpendProperty(amount=1, unit="USD"),
                ),
                # 1% of 1 USD is the first cent of real spend (after credits).
                notifications_with_subscribers=[
                    notify("ACTUAL", 1),
                    notify("ACTUAL", 100),
                    notify("FORECASTED", 100),
                ],
            )

        CfnOutput(self, "ApiUrl", value=api_base)
        CfnOutput(self, "StateMachineArn", value=sm.state_machine_arn)
        CfnOutput(self, "AmplifyAppId", value=web.attr_app_id)
        CfnOutput(self, "WebUrl", value=f"https://{branch.branch_name}.{web.attr_default_domain}")
        CfnOutput(self, "BucketName", value=bucket.bucket_name)
        CfnOutput(self, "TableName", value=table.table_name)

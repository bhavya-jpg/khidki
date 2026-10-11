"""DynamoDB single-table store (docs/SPEC.md §12). Same interface as MemoryStore.

Works against real AWS, LocalStack (set AWS_ENDPOINT_URL=http://localhost:4566) or moto in tests. Items keep
natural attributes (numbers as DynamoDB numbers), so they read well in the console.
"""

from __future__ import annotations

import os
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

from khidki_services.store import Item


def to_dynamo(x: Any) -> Any:
    if isinstance(x, bool) or x is None or isinstance(x, str):
        return x
    if isinstance(x, float):
        return Decimal(repr(x)) if x == x and abs(x) != float("inf") else None
    if isinstance(x, int):
        return x
    if isinstance(x, dict):
        return {k: to_dynamo(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [to_dynamo(v) for v in x]
    return x


def from_dynamo(x: Any) -> Any:
    if isinstance(x, Decimal):
        return int(x) if x == x.to_integral_value() and "." not in str(x) and "E" not in str(x) else float(x)
    if isinstance(x, dict):
        return {k: from_dynamo(v) for k, v in x.items()}
    if isinstance(x, list):
        return [from_dynamo(v) for v in x]
    return x


def create_table(name: str, resource: Any = None) -> Any:
    """For local mode and tests. In the cloud, CDK creates the table."""
    ddb = resource or boto3.resource("dynamodb", endpoint_url=os.environ.get("AWS_ENDPOINT_URL"))
    table = ddb.create_table(
        TableName=name,
        KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}, {"AttributeName": "sk", "KeyType": "RANGE"}],
        AttributeDefinitions=[
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    table.wait_until_exists()
    return table


class DynamoStore:
    def __init__(self, table_name: str | None = None, resource: Any = None) -> None:
        ddb = resource or boto3.resource("dynamodb", endpoint_url=os.environ.get("AWS_ENDPOINT_URL"))
        self.table = ddb.Table(table_name or os.environ.get("KHIDKI_TABLE", "Khidki"))

    def put(self, pk: str, sk: str, item: Item) -> None:
        self.table.put_item(Item=to_dynamo({**item, "pk": pk, "sk": sk}))

    def get(self, pk: str, sk: str) -> Item | None:
        got = self.table.get_item(Key={"pk": pk, "sk": sk}, ConsistentRead=True).get("Item")
        return from_dynamo(got) if got else None

    def query(
        self,
        pk: str,
        sk_prefix: str = "",
        limit: int | None = None,
        newest_first: bool = False,
        sk_from: str | None = None,
    ) -> list[Item]:
        if sk_from is not None:
            cond = Key("pk").eq(pk) & Key("sk").gte(sk_from)
        elif sk_prefix:
            cond = Key("pk").eq(pk) & Key("sk").begins_with(sk_prefix)
        else:
            cond = Key("pk").eq(pk)
        kwargs: dict[str, Any] = {
            "KeyConditionExpression": cond,
            "ScanIndexForward": not newest_first,
            "ConsistentRead": True,
        }
        out: list[Item] = []
        while True:
            resp = self.table.query(**kwargs)
            for it in resp.get("Items", []):
                if it["sk"].startswith(sk_prefix):
                    out.append(from_dynamo(it))
                    if limit is not None and len(out) >= limit:
                        return out
            if "LastEvaluatedKey" not in resp:
                return out
            kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

    def update(self, pk: str, sk: str, fields: Item) -> None:
        names = {f"#f{i}": k for i, k in enumerate(fields)}
        values = {f":v{i}": to_dynamo(v) for i, v in enumerate(fields.values())}
        self.table.update_item(
            Key={"pk": pk, "sk": sk},
            UpdateExpression="SET " + ", ".join(f"#f{i} = :v{i}" for i in range(len(fields))),
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
        )

    def delete(self, pk: str, sk: str) -> None:
        self.table.delete_item(Key={"pk": pk, "sk": sk})

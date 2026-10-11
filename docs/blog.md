# The children's breath is the sensor: building Khidki on AWS in four days

*Built for Environmental Hacks (WeMakeDevs × AWS, Bharat Builds Tour), Air track.*

On a bad-air morning in Delhi, a teacher with 44 children has one question: open the window, or keep it
shut?

Both answers are wrong. Keep it shut, and the children's own breath pushes CO₂ past 2,000 ppm within one
40-minute period. The room turns stuffy and attention drops. Open it, and about 97% of the smog outside ends
up inside. Teachers decide by feel, usually by temperature.

**Khidki** (खिड़की, Hindi for "window") tells the teacher the exact minute to open or close, and then checks
that the air really changed. This post is about how it works, where AWS fits, and the four things that
fought back.

![The teacher's screen: one instruction, one tap](https://raw.githubusercontent.com/bhavya-jpg/khidki/main/docs/blog/teacher-screen.jpg)

## How it decides, with no hardware

The decision of *when* needs no hardware at all. Khidki keeps a physics model of the classroom: 44 children
add roughly 3,450 ppm of CO₂ an hour to a 166 m³ room, and each window setting has an air-change rate (0.7
an hour shut, 10 with both sides open). More air out also means more smog in.

Every morning at 06:00 it takes the outdoor air forecast (CAMS, through Open-Meteo) and the school
timetable, and runs dynamic programming over the day in 5-minute steps to find the plan with the best
balance of stuffy air and smog, in six changes or fewer. A teacher who is asked fifteen times a day stops
listening, so the number of requests is part of the cost.

![The physics twin and the plan it kept](https://raw.githubusercontent.com/bhavya-jpg/khidki/main/docs/blog/physics-twin.png)

School safety rules sit on top as **Cedar** policies. "Outdoor PE moves indoors when forecast PM2.5 is above
90" is a `forbid` with a `when` clause, not an `if` buried in a planner.

## How it checks, with no sensor on the window

This is the part I like most. When the teacher taps "I've opened them", how do you know they did?

You do not need a sensor on the window. The children's breath is a tracer gas. With one ordinary CO₂ meter
in the room, the *rate* at which CO₂ falls tells you the room's air-change rate, and that tells you how open
the room is. Khidki fits that rate with a closed-form least-squares fit, compares it with what the
instruction should have produced, and if only one side opened, asks for the other.

![Real readings from a run: a slow fall with one side open, a faster one with both](https://raw.githubusercontent.com/bhavya-jpg/khidki/main/docs/blog/verified-from-the-air.png)

In the demo the classroom and the meter are simulated; the outdoor air is real. The figure above is from a
run where the simulated teacher opened only one side: Khidki noticed, asked for the corridor side, and
verified after the second tap.

## Where AWS fits

![The deployed architecture](https://raw.githubusercontent.com/bhavya-jpg/khidki/main/docs/blog/architecture.png)

- **AWS Step Functions** runs every instruction. The `waitForTaskToken` callback is an exact fit for
  "wait for a human to tap a button". Then a Wait state gives the air time to change, a task fits the curve,
  and a Choice state branches to *Verified*, a follow-up, or a re-plan.
- **AWS Lambda** holds the engine (API, sensor ingest, daily planner, workflow task), behind an **API
  Gateway** HTTP API, with state in one **DynamoDB** table.
- **EventBridge Scheduler** starts the 06:00 plan with a cron in `Asia/Kolkata`, so there is no UTC
  arithmetic.
- **Amazon Polly** speaks the instruction in Hindi (the Kajal neural voice), cached in S3.
- **Cedar** decides the policies, **Powertools for AWS Lambda** handles routing, logs and metrics, and the
  whole stack is one **AWS CDK** app in Python.

## What fought back

### 1. The "verification hold" that was a region lock

For a day, every AWS call failed with "explicit deny in a service control policy". I assumed my new account
was still being verified. It was not. Accounts created through the new sign-up experience carry a managed
policy that denies almost everything outside one home region, and mine was not Mumbai. I found it by probing
DynamoDB in every region until one answered: `ap-southeast-2`. So a Delhi product is hosted in Sydney. If
you are starting a hackathon on a fresh account, check which region actually answers before you write any
infrastructure code.

Amazon Bedrock had its own lock: "Operation not allowed" on every model, which only a Support case can
lift. Khidki's question-answering agent is written with the Strands Agents SDK, with a guard that rejects any
number not present in tool output, but on this account it answers from verified templates and says so.

### 2. The tracer-gas trick has blind spots

Running a whole simulated morning found bugs the unit tests did not:

- Just after closing, indoor CO₂ is only about 200 ppm above outdoor, and a sensor's ±3% error is enough to
  read "closed" as "slightly open". Closing is now verified against a boundary, not a point.
- "Go from both sides to one side" passed while both were still open, because the check ignored direction.
- During PE the room was empty, and Khidki "verified" a closing from a flat line. An empty room near outdoor
  CO₂ now counts as inconclusive, and nobody is asked to act on an empty room.

One is still open: when the fit is inconclusive, Khidki trusts the tap. An audit I ran on the last evening
caught the one-side case being missed in three of six runs, depending on timing. That is next on the list.

### 3. The benchmark said "trade-off", not "win"

I wanted the headline to be "less pollution". On 48 real Delhi school days in a simulated classroom, against
a CO₂ alarm, Khidki cut stuffy minutes from 65 a day to 17 with 4 requests to the teacher instead of 15.
But it let in slightly *more* PM2.5: 93% of an always-open room against the alarm's 89%.

Physics explains it. 44 children need about 3.3 air changes an hour, and at that rate indoor PM2.5 is
already near the outdoor level. Without a purifier, window timing cannot cut smog much. So the honest
headline is fewer stuffy minutes and fewer interruptions, and the product says that on its own landing
page.

### 4. Cedar will tell you which policy decided, if you ask

Cedar's diagnostics list internal ids like `policy0`. Add `@id("S2")` annotations and read them back through
the diagnostics, and every decision carries a human policy id. Add `@en` and `@hi` annotations and the policy
file also holds the bilingual explanation. The principal's page shows "PE moved indoors, S2, forecast 97"
straight from the policy, with no language model involved.

One more Cedar lesson: "a principal manages their own school" is not `resource in principal`. Rooms belong
to schools, not to users. Give the user a `school` attribute and write `resource in principal.school`.

## What I would do next

Put a real CO₂ meter in a real classroom for a week. Everything above is a simulation on real outdoor data,
and it is labelled that way everywhere, but a teacher's first reaction is worth more than another benchmark.

For schools with no sensor at all, Khidki already prints the day's window timetable on one A4 page. That may
turn out to be the feature that matters most.

*Code: [github.com/bhavya-jpg/khidki](https://github.com/bhavya-jpg/khidki). Built with Claude Code as an AI
coding assistant. Outdoor air data: CAMS via Open-Meteo, CC BY 4.0. Khidki is not a medical device.*

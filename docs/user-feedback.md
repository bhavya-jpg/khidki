# Teacher feedback kit (for the DTU build day, Sat 10 Oct)

Ten minutes with one or two teachers (or anyone who has taught in a Delhi classroom) is worth more to the
judges than another feature. Show the real app, ask, write down what they say word for word.

## Before you start
- Open `http://localhost:5173/teacher/6B?theme=light` on a laptop or tablet, scenario `partial_open`
  (`python tasks.py local partial_open`). Have the school page and the benchmark chart ready too.
- Ask for consent (below). No photos of faces without separate permission. Don't record children.
- Say up front: the classroom is simulated; the outdoor air is a real day from November 2025.

## Consent (read aloud, note the answer)
> "We're students building a tool for teachers on bad-air days, for a hackathon. Can we write down your
> comments and, if you agree, quote you by first name and role (for example 'Meena, Class 6 teacher') in our
> project video and write-up? You can say no, or ask us to quote you anonymously."

Record: name or "anonymous" · role · school type (government / private, no school name) · yes/no to quote.

## Show (3 minutes)
1. The quiet "keep shut" screen. Then an instruction arrives: "दोनों तरफ़ की खिड़कियाँ खोलिए".
2. Let *them* tap "खोल दीं". Watch: Khidki notices only one side opened and asks for the corridor side.
3. Ask Khidki: "Kya 11:20 pe PT bahar le jaun?" Show the answer with the policy and the numbers.

## Ask (5 minutes), and write the answers down word for word
1. On a bad-air day, how do you decide whether to open the windows today?
2. Would you follow an instruction like this one? What would stop you?
3. Is once or twice a period too much? How many interruptions a day is acceptable?
4. Is anything on this screen confusing? Is the Hindi natural?
5. "Can't right now" reasons: too cold, too noisy, raining, exam. Is anything missing?
6. Who would decide to use this in a school: you, the principal, the SMC, the DoE?
7. One sentence: would this help? Why or why not?

## After
- Put the quotes (only with consent) in `docs/user-feedback-notes.md` and the strongest one in the README and
  the video's closing card.
- Turn every "this confused me" into an issue and fix the top one before the video.
- Be honest in the write-up: "We showed it to N teachers on 10 Oct; here's what they said."

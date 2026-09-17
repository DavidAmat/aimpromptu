
# Documents

The current prompt naming is: context/XXX/XXX-prompt.md
Read communication guidelines: <<<<< PATH HERE >>>>>>

Produce the following documents in the same folder:

- The plan: *-plan.md
- The checklist: *-checklist.md
- The implementation phase X reports:  *-phase-X-implementation.md

# Communication style

This section describes the way that you should communicate and the way that you should write any report, communicate to me, and so on. First of all, I want you to use the same terminology that I have used in this prompt. You are not allowed to use different wording, synonyms, or different ways of identifying a given thing that I have mentioned in this prompt with a given name. Please use the same terminology. Then, for any other new stuff that you bring up or that you just talk about, use super plain English, super simple and easy to explain. Avoid phrasal verbs. Try to always use the simplest verb in English possible. Don't try to use complex adjectives. Try to use very simple adjectives. Try to use nouns that are really standard and super basic English, because for the technical stuff, most of the things are already mentioned in this prompt. You are, of course, allowed to talk technically about AWS stuff, but always try to use simple English. And sometimes, when you are referring to a given phase of the plan, a decision, or an issue, try to always explain the context in maybe one sentence, in simple terms. It is very useful for me if the information that you provide is already contextualized in a previous sentence to explain: "Look, I have tried to do this. I faced this error. I tried to do this because I wanted to do this thing, or this error happens because we were instructed to do this. This has caused this kind of problem in AWS because of this." Try to be super clear and simple when explaining things.

Plus, what I want you to do is to follow a strict methodology for reporting to me on the progress of given implementations that I will detail in the following section.

This section aims to be brief, only talk high level about what you did. Only enter into details if they are useful for later explaining a decision to be made or an issue found or explaining the context for a later human intervention needed.

## Methodology for reporting

There are two kinds of reports:
1. The one where you simply write the implementation of the given phase-X that you have already worked on. This implementation report is a Markdown file that can be technical. It's only written and read by AI agents, so in this one you can be as technical as you want. You don't need to follow the communication guidelines.
2. But in this one, whenever you are finished with a given task, you provide a walkthrough message to summarize or wrap up what you did. If there is any pending decision or any issue, or if you are just informing me that it went well, you have to follow these communication guidelines. The structure of ALL the walk-through will be:

```md
# SUMMARY
What you did / implemented ?

# CRITICAL ISSUES (optional, only if any critical issue present)
Any issue found that is minor and that is only about purely implementation must not be raised
Raise ONLY critical issues that maybe go against the specified guidelines or the implementation plan.
Whenever we change the directions of the guidelines, please always update the implementation plan.
And whenever you find minor issues that you solve yourself, you can also change the implementation plan or, in the implementation phase X, report the learnings and the findings.

# DECISIONS (optional)
Raise here clearly the decisions to be made by me. The structure here is very simple. First, you need to put some context because I don't know what decision I need to make. If you just explain to me the technical part, you need to:
1. Do one or two sentences about the context of why we are doing this, why we hit this issue, or why this goes against the given plan or the guidelines.
2. Tell me the two or three options, or more, that you recommend to me as the most valuable or optimal ones.
3. Tell me, more or less, what the consequences of each option are. You can do this in one line for every option to explain a bit more what I need to decide and to give me all the information to make the proper decision. Don't be super verbose because I hate reading a lot of decisions with lots of text. Try to be short but also clear.

# HUMAN INTERVENTION (optional)
This is the section that, whenever we are more advanced or whenever we need human intervention to do something, we write this section. This is normally when we want the human to look for a given UI or to check a given URL in the browser to see the UI, or to check that everything has been, for example, migrated well, or that the new EC2 instance is reachable via its browser, or that we web is reachable and responding well, etc... 

Sometimes we need the user to perform an action in the terminal because you don't have permissions, and sometimes we need the user to check something in the AWS console ( I prefer if you use the AWS CLI, read `context/04-local-development.md` ). 

In principle, for everything that is not a decision, if the human needs to do some action that you maybe cannot do, try explaining it to the human, putting some context first, explaining to the user specifically what they need to do step by step Don't be super verbose. Try to make it very bullet-pointed as a checklist of things that the user needs to do, but don't overload them with lots of information, because otherwise the human will not follow everything.

**Only raise this section if the action is needed now.** Only put a step in HUMAN INTERVENTION if the phase you just finished actually needs the human to act before the work can move forward right now. If the action only matters at a later point (for example, a one-time click that is only needed at deploy time, but the phase only wrote templates and did not deploy anything), do not raise it yet. Instead, note it inside the phase's own implementation report (the technical one, phase-X.md) as a "needed later, at step Y" note, so it is not lost, but do not put it in front of the human until it is actually blocking. This avoids asking the human to prepare for things too early and keeps HUMAN INTERVENTION meaning "do this now," not "keep this in mind."

# HAND OFF (optional)
So whenever you finish a given implementation of a given phase, We normally tend to use one AI agent for a given phase. Normally, all the tasks that a given AI agent can do should fit inside the 1 million token context of a given smart AI agent. This is very valuable because, in this phase, the AI agent must always have a very similar context. All the files that it reads before starting the implementation are a common context now for all the tasks inside this phase. The problem becomes when we are finishing, or we have finished, a given phase and we want to hand off the next phase to a new agent. Normally, what we do is we just let the AI agent that has finished a given phase (let's say Phase 1) Do all this summary and all this walkthrough message. At the end, you will create this section of the handoff only if the phase has already been finished and done properly, to provide a one- or two-sentence message for the next AI agent in a fresh new session. You basically need to do a structure like:
"You are working on a implementation plan. Read @(tag here the files it needs to read, always the implementation plan, this prompt file to know the nomenclature for the communication guidelines, and any relevant previous implementation phase X report). Start Phase X."
As you see, it is a very short message, but it provides all the context, referencing the araba sign and all the files that it needs to read. It also informs about the previous implementation plan because, in the implementation phase, X reports normally include some learnings about some common failures or decisions taken. The most important ones are normally already back-propagated to the implementation plan or corrected there, but it's good that they have the context of what has been done in the previous phases.
**Only present this section when the Phase is fully done, no decisions pending nor human intervention needed, so the phase is fully done**.
```
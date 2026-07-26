# Context

We have a set of disorganized feature requirements for this project in `project-features.md`. This document is a raw document, all what is explained there or in other mentioned documents should be detailed in the `plan` but in a well-written and organized way.

There will be a smart LLM that will take all these Features and create an implementation plan without implementing anything, simply organizing the features list in a better, well explained and technical manner such that the executors (other LLMs) can run and start implementing.

The goal is to end up with:
- an implementation technical plan in `context/implementations/plan`: this is just a folder, you should create folders to organize here the files. This is done by the LLM that will organize the features and create a smart plan.
- a progress documentation of whenever a worker LLM starts working on a given Epic/Story/Task `context/implementations/progress`.

# The Organizer

The LLM will act as a professional organizer to produce epics, stories, tasks and subtasks, similar to the one in Jira:

```
Initiative
└── Epic
    ├── Story
    │   ├── Task
    │   │   └── Subtask
    │   └── Task
    └── Story
```
- **Initiative**: An Initiative is a goal that usually takes months has many dependencies. We are not working on a cross domain project, we don't need initiatives here.
- **Epic**: tends to be one major feature
- **Story**: tends to work on a specific feature, something that is visual or that does a specific thing under the hood.
- **Tasks**: to implement a feature sometimes you need to break down the problem in small implementations, these are tasks. Some tasks may have several stages to be completed, or must start simple to then scale to a more robust solution, or start with a MVP, or a skeleton of what you need, test it with your final app in a simplified way and then come back to incrementally add new implementations to finalize that part of the feature, etc... This act of breaking a task is what produces the **sub-tasks**

Instructions here:
- The documents will be markdown files.
- We will use the minimal formatting as possible: only headers allowed, only in very few cases you are allowed to use bold, don't use italics (prefer to use quotes), use code blocks to produce anything that is code, try not to be very verbose in the code blocks simplify as much as possible the code inside to only what you want to show. 
- try to only use tables when necessary, otherwise simply use bullet points.
- try to use a understandable language, do not talk as a caveman, avoid being super verbose in your explanations but also try to opt for an English that can be easily understood. You are allowed to use technical coding/algorithmic/musical/etc... words as you require them.
- try to avoid creating very lengthy files. Use the hierarchy of the Jira notation as the way to organize folders. Epics can be folders, story nested folders and each task 1 markdown file, and use the header separators for the Subtasks. Each Epic should have a markdown file called `epic-<shortname>-index.md` to indicate high level in a short format what each story and task is organized in.

Apart from the markdown files and the folder structure within this plan/ folder we will also get as an output two files:

## Checklist
File: `context/implementations/plan/checklist.md`

Create a context/implementations/plan/checklist.md file to detail all the tree of tasks. In 2-3 sentences next to each epic describe what each epic is and the paths of the indexes of each epic (do not repeat all the detail that is inside the `epic-<shortname>-index.md` files, simply create this index file as a super quick look-up with 2-3 sentence only per each epic). Header 1 will be for epics. Header 2 will be for stories. Within a story we will have a checkbox of the **status** of this story, only ticked if all the tasks and subtasks are completed. Finally put as bullet points the tasks (simply put in bold the task short name and a 1 sentence description of it) and put in fron a checkbox to be ticked once completed:

Nomenclature of **status** (letters within the brackets):
- [x]: completed
- [p]: in progress
- [b]: blocked (we may need to come back later because of a blocker to be solved first, indicate it)
- [c]: cancelled (if we decide not to implement it, indicate why it was cancelled)

```md
# [] Epic 1 
<short description>
## [x] Story 1.1
<short description>
- [x] Task 1.1.1 **<short title>**:  <short description>
- [x] Task 1.1.2 **<short title>**:  <short description>
    - [x] SubTask 1.1.2.1 **<short title>**:  <short description>
    - [x] SubTask 1.1.2.2 **<short title>**:  <short description>
## [p] Story 1.2
<short description>
- [p] Task 1.2.1 **<short title>**:  <short description>
```

Put numbers to the epics, stories and tasks (i.e task 1.1.1 belongs to story 1.1 that belongs to epic 1)

## Sytem prompt for the workers
File: `context/implementations/plan/system-prompt-workers.md`

Once the organizer finishes the organization of all tasks we will dispatch the work to another LLM that will start working on the first feature. Depending on the granularity and complexity of the tasks we will start by one or another. We recommend doing a summary of what are we doing, the context of the project, how we have structured our organization (mention the index file so that the LLM can navigate to all the plan easily) and create a placeholder there for the task to work on. Once we instantiate a worker LLM to take a given task, we will tell which Epic > Story > Task to work on so that it will have the correct set of instructions, it will know were to look at the `context/implementations/plan` folder and will be able to look for the `context/implementations/progress` to see so far what has been implemented.

**Progress**:  We will need to instruct the worker to always fulfill at the end of this implementation the summary of what he has done and any main errors found, how they solve it, any architectural / software / feature-level change that was done during the process. This happens a lot, requirements change or due to some limitations we tend to opt for a different path or different requirements, we should be flexible.  The worker is also allowed to modify the plan `context/implementations/plan/` and also update the `epic-<shortname>-index.md` if that change of requirements affect a high level decision too. The system prompt should contain all the tools to both implement, get what it needs to be done, and have the autonomy to change plans (only if the human supervisor has agreed to do so of course, do NEVER change autonomously the requirements specified in the plan).

**Documentation folder**: as stated in `context/00-documentation-instructions.md` we have a two-split documentation folders. We will only use by now the `context` folder because we are still implementing. Once everything is mature we will document it (make it the very very last epic of all the plan) in the `documentation` folder. Meanwhile, all the workers should look at the `progress` folder to understand at which point we are (i.e the checklist as the main file to be looked up). 

**Checklist update**: make sure the workers update the checklist `context/implementations/plan/checklist.md` after finishing (once starting, put that is in progress). This way by only looking at checklist I can know the current status point of this project implementation. 

**Human in the loop**: most of the implementations will be UI driven. The user can record some audio and see how it renders. It is a very good practice that after a feature is completed, a given step of manual trial is done. It will be great if it instruct the human what to play in the piano (try always the very simplest MVP to test the functionality works well) and then it can test it. This is why it is important to have as a first implementation the recording capabilities because once we start working on rendering features, we will have to trial and error with the human in the loop a lot.

This way the worker will have all the context necessary regarding the implementation it needs to do. Now we need to also instruct the worker about the technical decisions.

## Tech Stack
File: `context/02-tech-stack.md`

During the plan you should make decisions around the technology to use: 
- python modules: I like using pydantic models, create also pre-commit checks like `mypy` and basic linting like `flake8` (try to ignore the typical long line errors or errors that are minor) and also use `black`. This should ensure that whenever we commit these are executed and we guarantee a good CI. We are going to push changes to `master` directly since we are the only contributors right now of this repo. I also like having `tqdm` progress bar for things like processing that take more than 10 seconds, this way also in the UI we can have ways to stream from the backend the status of the conversion of a file or the processing of something to have a more valid user experience. For backend we are using simple `FastAPI` endpoints. In the future we will containerize this but this is just a POC, don't work on doing best practices of backend yet, focus on being functional.
- frontend: see the current `aitu-frontend`. We are not looking for a professional website, try to make the UI beautiful and user-friendly but do not aim to have a really professional-grade website, this is just a PoC. Try to stick to one library for the components creation and make it standard across all pages. For example I recommend using `Aceternity UI` and `MUI X` components. Color palette in `context/colors/color-palette.md`. 
- coding conventions: tell the worker to read this file as context first `context/09-coding-conventions.md`  
- local development: we should tell in a short way the worker how we work locally as a summary of `context/04-local-development.md` (reference the file in case it has some problems).
- music transcription: see the research document we produced in `context/research/piano-transcription/piano-transcription-python-solutions.md` so that the main technologies we try (let's try one first, if I see the result and I complain and we find limitations on a given approach, we will move to another technology, there are several so let's try to go with the one that enables us do all what we want and if we hit blockers we will either go to another or simply modify a bit requirements). A key decision is how to save the matrices in a way that they occupy very few space, but they can be easily converted into dense matrices or be transformed back to sparse ones easily. Also how we save the matrix of each hand (Right and Left)

Remember this is a local PoC, don't think of production yet, let's try to have this running here locally in this Mac first.

## Project Complete Overview
Files: `context/00-project-complete-overview.md`, `context/01-project.md`

Ensure these file is up-to-date with all the features we want to implement in the Plan

## File Storage

Enable the storage as. the `aitu-backend/data` folder here locally. See `context/07-database.md`. Lightweight files there can be committed, heavy ones will need to be gitignored.

## Starting epic: skeleton

I recommend the first epic is setting the main skeleton of the project.
The project already exists. There is a backend and a frontend.
We simply have created one single page in which we rendered there the music as a simple MVP.
Feel free to delete it and start from scratch but at least you see the kind of architecture that has worked.
Your initial epics should be focused on designing the skeleton and the very simple components of what we need so that the later epics can focus on building on top of what the skeleton just already build. This way a single epic can design how it wants everything structured and the rest will simply fill the actual code.
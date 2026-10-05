# Implementing App context

Read @context/app/01-app-context.md. This is the desired app we want to build. 
You are not starting from scratch so take as starting point the current status of this repo.

## Plan

Read the @context/language/communication-implementation-plans.md and @context/language/communication-style.md, use them as reference.

Produce the implementation plan for everything that needs to be build.

While you work on each phase, please try to identify the documentation docs that should be updated, there are many things we started documenting when this was a simple PoC. This is not anymore a PoC, we are building a local web app at this stage, we are not building yet the final production version, but we want the documentation to not be stale. Read the `context/00-documentation-instructions.md` for the way I want the documentation to be written.

## Storage path

See that my ubuntu machine (read `context/02b-local-setup.md`) has some SSD that is `1.9TB` so that in principle we should have a kind of a `.database` folder that we gitignore in this repo that will live locally in this folder and that will be ignored in git but that it will easy to port to another machine if we compress and decompress this database. The idea is that this database is portable and self-contained in the sense that any person that downloads the repo in another machine and configures this `.database/` folder will have everything at its disposal. This will be ideal if at some point we want to port this into a production system in the cloud, we will simply need to attach a volume to the instance running this app, but this is future work. 

# Frontend Design

Read `context/implementations/01-mvp/09-minimal-ui/09-prompt.md` and `context/implementations/01-mvp/09-minimal-ui/09-minimal-ui-guidelines.md`. This can be one of the first phases of your migration. Before moving to any new architecture we must clean the UI. The current UI is full of bloated text, the user is overloaded with many details of technical things that it may not be aware of, so the UI is very unintuitive, cluttered with lots of text, 0 intuitive, it does not have any logical flow, it is not minimal (few buttons and clear sections, buttons only appear if needed or if we navigate to the right places of the app, etc...). So overall you should use your skill for frontend design whenever you need to decide on the UI of any page.

I suggest you re-design completely the app, in the sense of having a navbar, a user login / authentication, very clear sections on a lateral navbar, it should be very clear where to go for the different functionalities we have:
- Projects
- Music Library
- ... (figure out what is the most optimal parent - children relations here to structure this web app in a logical flow)

As a Frontend Design style I would tell you to try to copy the white / black / gray styles that OpenAI has. This offers clean, minimal UI's, we don't let very strong colors in unless very subtle things so that overall the app is not cluttered with lots of colors.
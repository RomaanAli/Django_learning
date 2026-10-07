"""
Seed the extra E-Learning courses and their lessons.

The catalogue this command installs:

* Computer Networks (4 lessons)
* Programming Fundamentals (4 lessons)
* RESTful API (5 lessons)
* Software Engineering Concepts (4 lessons)
* Software Project Management (5 lessons)
* Artificial Intelligence (5 lessons)
* Machine Learning (6 lessons)
* Deployment (3 lessons)

This is an *idempotent* management command: it is completely safe to run it
many times. Every course and lesson is looked up with ``get_or_create``, so
re-running the command never creates duplicate records and it never touches
courses that already exist in the database under the same title.

Usage:

    python manage.py seed_courses
"""

from decimal import Decimal

from django.core.management.base import BaseCommand

from courses.models import Course, Lesson

COURSES = [
    {
        "title": "Computer Networks",
        "description": (
            "Learn how computers talk to each other. This beginner course "
            "covers network types, topologies, the OSI and TCP/IP models, "
            "and the IP addressing ideas that keep the internet running."
        ),
        "price": "1800.00",
        "lessons": [
            {
                "title": "Introduction to Computer Networks",
                "content": (
                    "A computer network is a collection of devices - computers, "
                    "phones, printers and servers - connected together so they can "
                    "share data and resources. When you send a message, watch a video "
                    "or visit a website, your device is using a network to deliver that "
                    "data to another machine, often on the other side of the world.\n\n"
                    "Networks are everywhere. Your home Wi-Fi is a network, the "
                    "computers in a school lab form a network, and the internet itself "
                    "is simply the largest network of all - a global system of smaller "
                    "networks joined together.\n\n"
                    "In this lesson you will learn what a network is, why it matters, "
                    "and the vocabulary used in the rest of the course. Along the way we "
                    "will look at everyday examples, so the ideas stay concrete and easy "
                    "to picture.\n\n"
                    "Key takeaway: a network lets devices exchange information, and "
                    "every part of your digital life depends on one."
                ),
            },
{
                "title": "Network Types and Topologies",
                "content": (
                    "Networks come in different sizes, and their size usually decides "
                    "their name. A Personal Area Network (PAN) covers a single person's "
                    "devices, such as a phone and a smartwatch. A Local Area Network "
                    "(LAN) connects devices in one building, like an office or a school. "
                    "A Metropolitan Area Network (MAN) spans a city, and a Wide Area "
                    "Network (WAN) can cover countries - the internet is the biggest "
                    "WAN of all.\n\n"
                    "Topology describes how the devices on a network are arranged. In a "
                    "bus topology every device shares one cable, in a star topology all "
                    "devices connect to a central switch, in a ring topology each device "
                    "connects to two neighbours, and in a mesh topology devices link to "
                    "many others for extra reliability.\n\n"
                    "Real networks usually mix these ideas: a home network looks like a "
                    "star with a router in the middle, while large companies use "
                    "mesh-style links between buildings so a single failure cannot bring "
                    "everything down.\n\n"
                    "Key takeaway: network types describe size and scope, while "
                    "topologies describe shape and reliability."
                ),
            },
{
                "title": "OSI and TCP/IP Models",
                "content": (
                    "When two computers communicate, a lot has to happen: the data must "
                    "be broken into pieces, addressed, routed, delivered and finally "
                    "re-assembled into something readable. To manage this complexity, "
                    "networks are organised into layers, and each layer only worries "
                    "about its own job.\n\n"
                    "The OSI model describes seven layers, from the physical cable at "
                    "the bottom to the applications you use at the top: Physical, Data "
                    "Link, Network, Transport, Session, Presentation and Application. "
                    "You do not need to memorise all seven, but the idea is that each "
                    "layer builds on the one below it.\n\n"
                    "The TCP/IP model is the practical model the internet actually uses, "
                    "and it squeezes those seven layers into four: Link, Internet, "
                    "Transport and Application. When you open a website, TCP and IP (the "
                    "two protocols the model is named after) handle reliable delivery "
                    "and addressing, while the application layer carries protocols "
                    "like HTTP.\n\n"
                    "Key takeaway: layered models break networking into smaller, easier "
                    "jobs, and TCP/IP is the model behind the real internet."
                ),
            },
{
                "title": "IP Addressing and Basic Networking Concepts",
                "content": (
                    "Every device on a network needs an address, just like every house "
                    "on a street needs one. An IP address is that address. IPv4 "
                    "addresses look like 192.168.1.10 - four numbers between 0 and 255 - "
                    "while the newer IPv6 format, such as 2001:db8::1, was created "
                    "because we ran out of IPv4 addresses.\n\n"
                    "Some IP addresses are private: they are only used inside a home or "
                    "office (for example, addresses starting with 192.168.). Others are "
                    "public: they are unique on the internet and let other machines find "
                    "your network. Your home router uses one public address on the "
                    "internet and hands out private addresses to your phone, laptop "
                    "and TV.\n\n"
                    "Two more ideas are good to meet early. A subnet mask (like "
                    "255.255.255.0) groups addresses into a network, and DNS - the "
                    "Domain Name System - translates friendly names like "
                    "www.example.com into the IP addresses computers actually need.\n\n"
                    "Key takeaway: IP addressing gives every device a unique identity, "
                    "and DNS lets humans use names instead of numbers."
                ),
            },
        ],
    },
{
        "title": "Programming Fundamentals",
        "description": (
            "A friendly, beginner-first introduction to programming. You will learn "
            "how programs work, how to store and manipulate data, and how to use "
            "conditions, loops and functions to solve real problems - no prior "
            "experience needed."
        ),
        "price": "1200.00",
        "lessons": [
            {
                "title": "Introduction to Programming",
                "content": (
                    "Programming is the art of giving a computer precise instructions "
                    "to follow. A computer will do exactly what you tell it - nothing "
                    "more, nothing less - so programmers learn to express tasks as "
                    "clear, ordered steps.\n\n"
                    "Programs are written in programming languages such as Python, Java "
                    "and JavaScript. Some languages are translated into machine code by "
                    "a compiler before they run, while others, like Python, are executed "
                    "line by line by an interpreter. The very first program most people "
                    "write simply prints a message to the screen.\n\n"
                    "You do not need a maths degree to start. All you need is a text "
                    "editor, a language installed on your computer, and curiosity. Every "
                    "expert programmer started with small examples and built up "
                    "from there.\n\n"
                    "Key takeaway: programming is about giving computers clear "
                    "instructions, and anyone can learn by starting small."
                ),
            },
            {
                "title": "Variables, Data Types and Operators",
                "content": (
                    "Variables are named boxes where a program stores information. "
                    "Instead of repeating a value everywhere, you write it once into a "
                    "variable and then refer to that name, for example: score = 10 "
                    "stores the number 10 under the name score.\n\n"
                    "Different kinds of data need different data types. The most common "
                    "are integers (whole numbers), floats (decimal numbers), strings "
                    "(text like 'Hello!') and booleans (true/false values). Most "
                    "languages are careful about types, because adding numbers is not "
                    "the same as joining text.\n\n"
                    "Operators let you work with that data. Arithmetic operators such as "
                    "+ and - do maths, while comparison operators such as == and < "
                    "compare values and give back a boolean. Once you can store data and "
                    "manipulate it, you can already write useful little programs that "
                    "calculate and transform information.\n\n"
                    "Key takeaway: variables store data, data types describe the kind of "
                    "data, and operators let you compute and compare."
                ),
            },
{
                "title": "Conditional Statements and Loops",
                "content": (
                    "Programs are rarely a straight line - they make decisions and "
                    "repeat work. Conditional statements let a program choose what to "
                    "do. An if statement checks a condition and runs one block of code "
                    "when the condition is true, and you can add else to handle the "
                    "false case. This is how a program decides if a number is even, or "
                    "whether a user is logged in.\n\n"
                    "Loops let a program repeat a block of work without copying it. A "
                    "for loop repeats a fixed number of times or once for each item in a "
                    "collection, while a while loop keeps repeating as long as a "
                    "condition stays true. Together they save programmers an enormous "
                    "amount of repetition.\n\n"
                    "Conditions and loops also combine well: you can loop through a list "
                    "of students and use conditions to check each one's score. That "
                    "combination - decide and repeat - is the heart of most real "
                    "programs.\n\n"
                    "Key takeaway: conditions give programs choices, and loops give them "
                    "repetition; together they handle almost any logic you need."
                ),
            },
            {
                "title": "Functions and Basic Problem Solving",
                "content": (
                    "A function is a named, reusable block of code that performs one "
                    "task. You give it inputs, called parameters or arguments, it does "
                    "its work, and it can send back a result with a return statement. "
                    "Once a function exists, you can call it from anywhere instead of "
                    "re-writing the same code.\n\n"
                    "Functions support the first rule of good programming: do not repeat "
                    "yourself. If several parts of a program need the same calculation, "
                    "one function can serve them all, and fixing a bug in that function "
                    "fixes it everywhere at once.\n\n"
                    "Solving problems with code follows the same habit you use anywhere "
                    "else: understand the problem, break it into small steps, write the "
                    "steps clearly, and test each piece before moving on. Functions are "
                    "the natural tool for that breakdown, because each function "
                    "represents one small, testable step.\n\n"
                    "Key takeaway: functions turn one task into a reusable, focused "
                    "piece of code, and breaking problems into small steps is the real "
                    "skill of programming."
                ),
            },
        ],
    },
{
        "title": "RESTful API",
        "description": (
            "Find out how modern apps share data with each other. This course covers "
            "the REST architecture style, HTTP methods and status codes, JSON, and the "
            "design and security best practices behind clean, reliable APIs."
        ),
        "price": "2200.00",
        "lessons": [
            {
                "title": "Introduction to APIs and REST",
                "content": (
                    "An API, or Application Programming Interface, is a set of rules "
                    "that lets one piece of software talk to another. In a restaurant, "
                    "the waiter is the API: you order from the menu, the waiter passes "
                    "your order to the kitchen, and the kitchen sends back the food. You "
                    "never need to know how the kitchen works.\n\n"
                    "A web API follows the same idea over the internet. When a weather "
                    "app shows tomorrow's forecast, it is not magically knowing the "
                    "weather - the app sends a request to a weather API, and that API "
                    "answers with the data.\n\n"
                    "REST (Representational State Transfer) is the most popular style "
                    "for building web APIs. A RESTful API treats data as resources, "
                    "uses standard HTTP operations on those resources, and keeps the "
                    "server stateless - meaning every request carries everything the "
                    "server needs to understand it.\n\n"
                    "Key takeaway: an API is a contract between two programs, and REST "
                    "gives that contract a simple, standard shape."
                ),
            },
            {
                "title": "HTTP Methods and Status Codes",
                "content": (
                    "Web APIs are built on HTTP, the same protocol your browser uses. "
                    "HTTP defines a set of methods that describe what you want to do "
                    "with a resource. The four you will use most are GET (read data), "
                    "POST (create data), PUT or PATCH (update data), and DELETE (remove "
                    "data).\n\n"
                    "Every response also comes with a status code, a three-digit number "
                    "that tells the client what happened. Codes starting with 2 mean "
                    "success (200 OK, 201 Created), codes starting with 4 mean the "
                    "client made a mistake (404 Not Found, 400 Bad Request), and codes "
                    "starting with 5 mean the server had a problem (500 Internal Server "
                    "Error).\n\n"
                    "Status codes matter because a client program needs to know whether "
                    "its request worked. A good API returns the right code for every "
                    "situation, which is why learning the common codes early makes you a "
                    "better API developer and consumer.\n\n"
                    "Key takeaway: HTTP methods describe the action you want, and status "
                    "codes describe the result of that action."
                ),
            },
{
                "title": "REST API Endpoints and Resources",
                "content": (
                    "In REST, everything you work with is a resource - a thing the API "
                    "knows about, such as a user, a product or an order. A resource has "
                    "a name and a unique identifier, so each one can be addressed "
                    "individually.\n\n"
                    "Resources live at endpoints: the URLs where you send requests. A "
                    "well-designed API uses clear, plural nouns in its URL paths. For "
                    "example, GET /api/users returns the collection of users, "
                    "POST /api/users creates a new user, and GET /api/users/42 fetches "
                    "the single user whose id is 42.\n\n"
                    "Following these conventions makes an API predictable. Once you know "
                    "one resource works a certain way, you can guess how every other "
                    "resource behaves, which is exactly why REST-style URLs feel so "
                    "friendly to learn and to use.\n\n"
                    "Key takeaway: endpoints are the addresses of resources, and "
                    "consistent, noun-based URLs make an API easy to understand."
                ),
            },
            {
                "title": "Request and Response Data with JSON",
                "content": (
                    "APIs send data back and forward, and today nearly all of them use "
                    "JSON. JSON is a lightweight text format built from key-value "
                    "pairs, which Python, JavaScript and every other language can read. "
                    "A JSON object looks like a dictionary or a JavaScript object, with "
                    "names in quotes followed by their values.\n\n"
                    "A request being sent to an API usually carries a method, a URL, "
                    "some headers and, when there is data to send, a body. The "
                    "Content-Type header tells the server the format of that body - "
                    "application/json is the standard for JSON APIs.\n\n"
                    "The response that comes back has the same shape: a status code, "
                    "headers, and a body containing the JSON data or a message. Tools "
                    "like Postman and curl let you build requests by hand so you can "
                    "test an API before you write any code against it.\n\n"
                    "Key takeaway: JSON is the shared language of APIs, and every HTTP "
                    "request and response is made of a few simple, learnable parts."
                ),
            },
{
                "title": "API Authentication and Best Practices",
                "content": (
                    "Many APIs protect data that should only be seen by authorised "
                    "people or apps. The simplest approach is an API key: a secret "
                    "string the client includes with each request so the server knows "
                    "who is calling. Token-based authentication, where the client logs "
                    "in once and receives a token to send with later requests, is the "
                    "pattern most modern APIs use.\n\n"
                    "Whatever method you choose, security should come first: always use "
                    "HTTPS so data cannot be read in transit, never put secrets in "
                    "client-side code or URLs, and store keys safely on the server.\n\n"
                    "Good APIs are also designed to last. Version your API (for example "
                    "/api/v1/) so changes do not break existing clients, limit how "
                    "often requests are allowed with rate limiting, and document "
                    "everything clearly. A good developer experience is part of the "
                    "product itself.\n\n"
                    "Key takeaway: protect APIs with clear authentication, and design "
                    "for the future with HTTPS, versioning and good documentation."
                ),
            },
        ],
    },
{
        "title": "Software Engineering Concepts",
        "description": (
            "Software engineering is about building reliable software in teams. Explore "
            "the discipline itself, the software development life cycle, popular "
            "development models, and how testing and maintenance keep systems healthy."
        ),
        "price": "1600.00",
        "lessons": [
            {
                "title": "Introduction to Software Engineering",
                "content": (
                    "Software engineering is the disciplined application of engineering "
                    "principles to building software. Programming is one part of the "
                    "job, but engineers also worry about design, quality, cost and "
                    "teamwork - the same concerns you would find in civil or mechanical "
                    "engineering.\n\n"
                    "Good software is not only correct; it is maintainable, reliable, "
                    "efficient and easy to understand. These qualities rarely happen by "
                    "accident. They come from clear requirements, thoughtful design, "
                    "careful implementation and constant review.\n\n"
                    "Software also has to survive real use. Users find unexpected "
                    "inputs, systems change, and requirements evolve. Engineering "
                    "practices such as testing, version control and design review exist "
                    "precisely so that software keeps working as it grows.\n\n"
                    "Key takeaway: software engineering turns individual coding into a "
                    "repeatable, team-oriented process that produces reliable software."
                ),
            },
            {
                "title": "Software Development Life Cycle (SDLC)",
                "content": (
                    "The Software Development Life Cycle (SDLC) is the sequence of "
                    "phases a software project moves through, from the first idea to "
                    "retirement. The classic phases are: requirements, design, "
                    "implementation, testing, deployment and maintenance.\n\n"
                    "During requirements, the team discovers what the software must do "
                    "and records it. Design plans the architecture - databases, "
                    "components and interfaces - before code is written. Implementation "
                    "is where programmers build the features. Testing checks that "
                    "everything works for real users, deployment puts the software into "
                    "the hands of those users, and maintenance keeps it working and up "
                    "to date afterwards.\n\n"
                    "Teams do not always follow the phases literally. Some workflows are "
                    "flexible and revisit earlier phases regularly, but every healthy "
                    "project still thinks through each of these steps at some point.\n\n"
                    "Key takeaway: the SDLC is the roadmap every software project "
                    "follows, from idea to maintenance."
                ),
            },
{
                "title": "Software Development Models",
                "content": (
                    "Development models are ways of organising the SDLC phases. The "
                    "Waterfall model is the classic sequential approach: each phase "
                    "finishes before the next begins. It is simple and easy to plan, "
                    "but it is rigid - if requirements change late, adapting is painful.\n\n"
                    "At the other end, iterative and incremental models build the "
                    "software in small cycles, delivering working pieces early and "
                    "improving them in later rounds. The V-model pairs each development "
                    "phase with a matching testing phase, which makes verification very "
                    "visible.\n\n"
                    "Modern teams mostly follow Agile approaches, which treat the "
                    "process as a series of short iterations with constant feedback. "
                    "There is no single best model: small, well-understood projects can "
                    "suit Waterfall, while products with changing requirements benefit "
                    "from iterative and Agile thinking.\n\n"
                    "Key takeaway: development models decide how strictly you follow the "
                    "SDLC phases, from sequential Waterfall to short-iteration Agile."
                ),
            },
            {
                "title": "Software Testing and Maintenance",
                "content": (
                    "Testing is how we gain confidence that software behaves as "
                    "expected. It is done at many levels: unit testing checks "
                    "individual functions in isolation, integration testing checks that "
                    "components work together, system testing checks the whole product, "
                    "and acceptance testing checks that the product really satisfies "
                    "the user's needs.\n\n"
                    "Regression testing - re-running tests after a change - makes sure "
                    "new code did not break existing features. Many teams automate "
                    "their tests so they run on every change, because automated tests "
                    "give immediate feedback to every developer.\n\n"
                    "Once software is released it still needs maintenance. Bug fixes "
                    "are corrective maintenance, adding features on request is adaptive "
                    "maintenance, and performance tweaks are perfective maintenance. "
                    "Well-tested code is dramatically easier to maintain, which is why "
                    "testing and maintenance are two halves of the same story.\n\n"
                    "Key takeaway: layered testing builds confidence in software, and "
                    "careful maintenance keeps that confidence alive after release."
                ),
            },
        ],
    },
{
        "title": "Software Project Management",
        "description": (
            "Learn how real software projects are planned, scheduled and delivered. "
            "This course covers the core ideas of project management - scope, time, "
            "cost and risk - plus the Agile and Scrum practices modern teams use "
            "every day."
        ),
        "price": "1900.00",
        "lessons": [
            {
                "title": "Introduction to Software Project Management",
                "content": (
                    "A software project is a temporary effort to build or change "
                    "software. Project management is the discipline of making sure that "
                    "effort is finished on time, within budget and to the expected "
                    "quality.\n\n"
                    "Every project balances three constraints: scope (what we build), "
                    "time (how long it takes) and cost (what it costs). Change any one "
                    "and the others feel the pressure - cut the schedule and cost goes "
                    "up, or scope must shrink. Good project managers keep this balance "
                    "visible and honest.\n\n"
                    "The project manager's job is less about writing code and more about "
                    "planning, coordinating people, clearing obstacles, tracking "
                    "progress and reporting status. Clear communication turns a group "
                    "of individuals into a team that delivers together.\n\n"
                    "Key takeaway: project management keeps scope, time and cost in "
                    "balance, while helping people work together effectively."
                ),
            },
            {
                "title": "Project Planning and Scope",
                "content": (
                    "Planning starts with scope: the full set of features and work the "
                    "project will deliver. A clear scope prevents a project from slowly "
                    "growing without control - a problem known as scope creep, where "
                    "extra features keep slipping in and deadlines slip with them.\n\n"
                    "A common planning tool is the Work Breakdown Structure (WBS), "
                    "which breaks the project into smaller and smaller pieces until "
                    "each piece is a task small enough to estimate and assign. "
                    "Deliverables - the concrete things the project produces - make "
                    "progress visible to everyone involved.\n\n"
                    "A project plan captures this in writing: the goals, the "
                    "deliverables, the tasks, who owns them and when they should be "
                    "done. It is a living document rather than a museum piece, updated "
                    "whenever the team learns something new.\n\n"
                    "Key takeaway: planning starts by defining scope, breaking work into "
                    "small tasks, and writing the plan down so everyone agrees."
                ),
            },
{
                "title": "Time, Cost and Resource Management",
                "content": (
                    "Time management turns the work list into a schedule. Each task gets "
                    "an estimate, tasks with dependencies are sequenced (some can run in "
                    "parallel, others must wait), and the team builds a timeline. Simple "
                    "estimates use rough effort units like story points; formal "
                    "projects often use Gantt charts and critical-path analysis to see "
                    "the whole schedule at a glance.\n\n"
                    "Cost management puts a price on the plan. The main costs are "
                    "people's time, but there are also tools, services and "
                    "infrastructure. Tracking planned versus actual cost tells you "
                    "early whether the project is on budget or drifting.\n\n"
                    "Resources are the people and equipment doing the work. Resource "
                    "management makes sure no one is overloaded, everyone has what they "
                    "need, and skills are matched to tasks. A schedule that ignores "
                    "resources is fiction.\n\n"
                    "Key takeaway: time, cost and resources are planned together so the "
                    "schedule is realistic and the budget stays under control."
                ),
            },
            {
                "title": "Risk Management",
                "content": (
                    "A risk is any uncertain event that could hurt the project - a key "
                    "developer leaving, a third-party service failing, or requirements "
                    "that turn out to be more complex than expected. Smart teams manage "
                    "risk instead of hoping problems will not happen.\n\n"
                    "Risk management has four steps: identify risks, assess how likely "
                    "each one is and how much damage it could cause, plan responses, and "
                    "monitor them throughout the project. High-likelihood, high-impact "
                    "risks get responses first.\n\n"
                    "Responses are usually one of four kinds: avoid (change the plan so "
                    "the risk cannot happen), mitigate (reduce the chance or impact), "
                    "transfer (move the risk elsewhere, such as to a vendor), or accept "
                    "(acknowledge it and keep a reserve). Writing risks down in a "
                    "simple register keeps them from being forgotten.\n\n"
                    "Key takeaway: risks are identified, assessed and planned for, so "
                    "surprises do not become disasters."
                ),
            },
{
                "title": "Agile and Scrum Project Management",
                "content": (
                    "Agile is a modern approach to project management built around "
                    "short iterations, continuous feedback and adapting as you learn. "
                    "Instead of one giant delivery, the team ships small, useful "
                    "increments over and over, listening to users after each one.\n\n"
                    "Scrum is the most popular way to run an Agile team. Work is "
                    "planned in sprints, typically one or two weeks long. The product "
                    "owner maintains a prioritised backlog of work, the team commits to "
                    "what it can finish each sprint, and short daily stand-up meetings "
                    "keep everyone aligned. At the sprint's end, the team reviews what "
                    "was built and reflects on how to improve.\n\n"
                    "Scrum keeps planning simple by letting the team adjust every sprint "
                    "rather than trying to predict months ahead. This is why Agile and "
                    "Scrum dominate modern software teams: they turn uncertainty into a "
                    "flow of small, deliverable improvements.\n\n"
                    "Key takeaway: Agile delivers value in short cycles, and Scrum adds a "
                    "simple structure of sprints, roles and ceremonies to make that work."
                ),
            },
        ],
    },
{
        "title": "Artificial Intelligence",
        "description": (
            "Discover how machines can think, reason and decide. This beginner "
            "course introduces intelligent agents, search and problem solving, "
            "knowledge representation, learning, and the ethical questions that "
            "come with building intelligent systems."
        ),
        "price": "2400.00",
        "lessons": [
            {
                "title": "Introduction to Artificial Intelligence",
                "content": (
                    "Artificial Intelligence (AI) is the branch of computer "
                    "science that builds systems able to do things that normally "
                    "need human intelligence - understanding language, "
                    "recognising images, planning and making decisions.\n\n"
                    "The idea is old: Alan Turing asked whether machines could "
                    "think back in 1950, and the term 'artificial intelligence' "
                    "was coined in 1956. Today AI works so well because three "
                    "things arrived together - huge amounts of data, fast and "
                    "cheap computing power, and much better algorithms. You "
                    "already use it in search engines, spam filters, photo "
                    "tagging, voice assistants and recommendation feeds. This "
                    "course explains how such systems are built, starting with "
                    "the classical ideas that need no machine learning at all.\n\n"
                    "Key takeaway: AI makes computers behave intelligently, and "
                    "modern success comes from data, computing power and better "
                    "algorithms together."
                ),
            },
            {
                "title": "Intelligent Agents and Problem Solving",
                "content": (
                    "An intelligent agent perceives its environment through "
                    "sensors and acts on it through actuators in order to reach a "
                    "goal. A thermostat, a chess program and a self-driving car "
                    "are all agents; only the complexity differs.\n\n"
                    "Many classical problems are solved by search. The state "
                    "space lists every situation the agent could be in, and "
                    "search algorithms explore it looking for a path from start "
                    "to goal. Breadth-first search goes level by level and finds "
                    "the shortest path when every step costs the same; "
                    "depth-first search uses less memory but may wander; informed "
                    "search such as A* uses a heuristic - an educated guess of "
                    "the remaining distance - to look in the most promising "
                    "direction first. Games add an opponent, so algorithms such "
                    "as minimax choose the move that is best even if the "
                    "opponent always plays perfectly.\n\n"
                    "Key takeaway: intelligence often means searching a space of "
                    "possibilities, and heuristics make that search practical."
                ),
            },
            {
                "title": "Knowledge Representation and Reasoning",
                "content": (
                    "For an agent to reason, its knowledge must be written in a "
                    "form a computer can use. A knowledge base holds facts and "
                    "rules, and an inference engine derives new facts from "
                    "them.\n\n"
                    "Propositional logic works with simple true or false "
                    "statements, while first-order logic adds objects, properties "
                    "and relations, so we can express 'every student who passes "
                    "all exams graduates'. Rule-based systems store knowledge as "
                    "IF-THEN rules and powered the expert systems of the 1980s, "
                    "which captured a specialist's experience as hundreds of "
                    "rules. Semantic networks and ontologies organise concepts "
                    "into graphs, which is how a search engine knows that a car "
                    "is a kind of vehicle. Symbolic reasoning is explainable - "
                    "you can point to the rules that produced a conclusion - but "
                    "writing enough rules for the real world is very hard, which "
                    "is why machine learning became so important.\n\n"
                    "Key takeaway: knowledge representation lets computers reason "
                    "with facts and rules, and keeps that reasoning explainable."
                ),
            },
            {
                "title": "Machine Learning and Deep Learning in AI",
                "content": (
                    "For decades AI was hand-written: people encoded the rules. "
                    "Machine learning reversed that. Instead of writing rules we "
                    "give the computer examples and let it find the patterns "
                    "itself.\n\n"
                    "This matters because some tasks have no practical rule list "
                    "- recognising a face, translating a sentence, understanding "
                    "speech - yet learning from millions of examples works "
                    "extremely well. Deep learning goes further with artificial "
                    "neural networks of many layers, which learn increasingly "
                    "abstract features: edges, then shapes, then whole objects. "
                    "AI and machine learning are therefore not rivals; machine "
                    "learning is one family of techniques inside AI, and it "
                    "drives almost all of the recent progress.\n\n"
                    "Key takeaway: machine learning is a subset of AI in which "
                    "patterns are learned from data instead of being programmed "
                    "by hand."
                ),
            },
            {
                "title": "AI Ethics, Applications and the Future",
                "content": (
                    "Powerful tools bring powerful risks. The best known is "
                    "bias: a model trained on unfair historical data repeats and "
                    "even amplifies that unfairness when it decides who gets a "
                    "loan, a job interview or medical attention. Other concerns "
                    "are privacy, because models learn from personal data; "
                    "opacity, because deep networks are hard to explain; and "
                    "misuse, from deepfakes to disinformation.\n\n"
                    "Good practice begins before any code is written. Ask what "
                    "problem is being solved, whose data is used, who could be "
                    "harmed, and how the result will be tested and monitored. "
                    "Keeping a human in the loop for high-stakes decisions, "
                    "documenting data sources and limitations, and letting "
                    "affected people appeal are practical safeguards. The people "
                    "who understand both the strengths and the limits of AI will "
                    "be the ones who use it well.\n\n"
                    "Key takeaway: AI is a tool whose value depends on how "
                    "thoughtfully it is designed, tested and governed."
                ),
            },
        ],
    },
{
        "title": "Machine Learning",
        "description": (
            "Learn how computers improve with experience. This course covers "
            "supervised, unsupervised and reinforcement learning, data "
            "preparation and feature engineering, the main regression and "
            "classification algorithms, honest model evaluation, and how to take "
            "a model into production."
        ),
        "price": "2800.00",
        "lessons": [
            {
                "title": "Introduction to Machine Learning",
                "content": (
                    "Machine learning means writing programs that improve with "
                    "experience instead of following hand-written rules. You "
                    "supply examples, the algorithm finds patterns, and the "
                    "result is a model that can make predictions about new "
                    "data.\n\n"
                    "Compare the two approaches for spam filtering. By hand you "
                    "would list suspicious words and rules, then keep patching "
                    "them as spammers adapt. With machine learning you show the "
                    "computer thousands of emails already labelled spam or not "
                    "spam, and it works out its own signals - signals that are "
                    "usually better and much easier to update. The same idea "
                    "powers recommendations, credit scoring, speech recognition "
                    "and fraud detection, wherever patterns are too complex to "
                    "write down as rules. It is not magic: relevant data, a clear "
                    "question and honest evaluation decide whether it works.\n\n"
                    "Key takeaway: machine learning finds patterns in examples, "
                    "and the data and the question matter more than the "
                    "algorithm."
                ),
            },
            {
                "title": "Types of Learning: Supervised, Unsupervised and Reinforcement",
                "content": (
                    "Machine learning splits into three families depending on "
                    "what feedback is available.\n\n"
                    "Supervised learning uses labelled examples, where each input "
                    "comes with the correct answer. When the answer is a category "
                    "- spam or not spam, cat or dog - the task is classification; "
                    "when the answer is a number - price, demand, temperature - it "
                    "is regression. This is the most common type in business.\n\n"
                    "Unsupervised learning uses unlabelled data and looks for "
                    "structure. Clustering groups similar items together, which "
                    "is how customers get segmented into behavioural groups, "
                    "while dimensionality reduction squeezes many features into a "
                    "few informative ones.\n\n"
                    "Reinforcement learning learns by trial and error. An agent "
                    "acts in an environment, receives rewards or penalties, and "
                    "gradually discovers a policy that maximises reward. It "
                    "powers game playing and robot control but needs a lot of "
                    "interaction.\n\n"
                    "Key takeaway: match the family to the data - labels mean "
                    "supervised, structure-seeking means unsupervised, and action "
                    "with reward means reinforcement."
                ),
            },
            {
                "title": "Data Preparation and Feature Engineering",
                "content": (
                    "Real data is messy, and preparing it is usually the biggest "
                    "part of a machine learning project. Expect missing values, "
                    "duplicates, impossible numbers, mixed units and text that "
                    "means the same thing in three different spellings.\n\n"
                    "Cleaning comes first: fix or drop bad rows, handle missing "
                    "values, and check that nothing leaks information from the "
                    "future into the past. Then engineer features that make "
                    "patterns easy to see. A date becomes day of week and "
                    "is-weekend; long text becomes word counts; scaling puts "
                    "features on comparable ranges so a salary in millions does "
                    "not drown out an age in tens. Finally split the data: "
                    "training rows to fit the model, validation rows to tune it, "
                    "and a test set kept untouched until the very end. Tuning "
                    "against the test set quietly turns it into training data and "
                    "gives you an over-optimistic score.\n\n"
                    "Key takeaway: good features and honest data splits matter "
                    "more than a fancy algorithm."
                ),
            },
            {
                "title": "Regression and Classification Algorithms",
                "content": (
                    "Two groups of algorithms cover most beginner projects.\n\n"
                    "Regression predicts a number. Linear regression fits the "
                    "best straight line through the data and is easy to "
                    "interpret, because each coefficient shows how much the "
                    "prediction moves when a feature changes. Regularised "
                    "versions such as ridge and lasso add flexibility while "
                    "discouraging the model from chasing noise.\n\n"
                    "Classification predicts a category. Logistic regression "
                    "estimates a probability and applies a threshold - simple, "
                    "fast and a strong baseline. Decision trees ask a series of "
                    "questions and are very readable, but a single tree overfits "
                    "easily. Ensembles fix that: random forests average many "
                    "trees, and gradient boosting builds trees one after another, "
                    "each correcting the previous one's mistakes. Boosted trees "
                    "win most competitions on tabular data.\n\n"
                    "Key takeaway: start with a simple, interpretable model as a "
                    "baseline, then try a tree ensemble and compare honestly."
                ),
            },
            {
                "title": "Model Evaluation and Overfitting",
                "content": (
                    "A model that scores perfectly on its training data has "
                    "usually just memorised it. Overfitting is the gap between "
                    "memorising and generalising, and evaluation is how we measure "
                    "that gap.\n\n"
                    "Accuracy alone is misleading. If only one percent of "
                    "transactions are fraudulent, a model that always answers "
                    "'not fraud' is 99 percent accurate and completely useless. "
                    "Confusion matrices, precision, recall and F1 show what "
                    "happens to each class, and ROC-AUC summarises ranking quality "
                    "across thresholds. For regression, mean absolute error and "
                    "root mean squared error give the average mistake in the "
                    "target's own units. To fight overfitting, use "
                    "cross-validation so every row is tested at some point, add "
                    "regularisation, gather more data, and drop redundant "
                    "features. Report the test result only once you have stopped "
                    "choosing.\n\n"
                    "Key takeaway: use metrics that match the real cost of "
                    "mistakes, and trust only results from data the model has "
                    "never seen."
                ),
            },
            {
                "title": "From Notebook to Production",
                "content": (
                    "A model that lives only in a notebook delivers no value. "
                    "Getting it into a product means agreeing what to build, "
                    "serving predictions reliably, and watching what happens "
                    "afterwards.\n\n"
                    "Start by defining success in business terms: a fraud model "
                    "may be judged on money saved rather than accuracy, and a "
                    "recommender on engagement rather than error. Then package the "
                    "trained model so other programs can call it - save it with a "
                    "tool such as joblib, expose it through a small API endpoint, "
                    "and keep the exact preprocessing steps beside it so training "
                    "and serving agree. Once live, monitor input distributions, "
                    "prediction volume, latency and error rates, because data "
                    "drifts as behaviour changes and a model can decay silently. "
                    "Version your models and data, log predictions so problems can "
                    "be explained, and plan how you will retrain and roll "
                    "back.\n\n"
                    "Key takeaway: the project is finished only when the model "
                    "runs in production, is monitored, and can be retrained "
                    "safely."
                ),
            },
        ],
    },
{
        "title": "Deployment",
        "description": (
            "Take your project from your laptop to a real URL. Learn what "
            "changes in production, how to deploy a Django app to a cloud "
            "platform, and how to manage secrets, logs, backups and updates once "
            "the site is live."
        ),
        "price": "1500.00",
        "lessons": [
            {
                "title": "Introduction to Deployment",
                "content": (
                    "Writing an application on your own computer is only half "
                    "the job; deploying means putting it somewhere other people "
                    "can reach it. In development you run a lightweight server "
                    "inside your project, with helpful error pages and your "
                    "machine's own database. In production the same code runs on "
                    "a real server behind HTTPS, with a proper database, real "
                    "secrets, and logging that records what happened.\n\n"
                    "The main differences are configuration and discipline. "
                    "Settings such as debug mode, allowed hosts, secret keys and "
                    "database credentials must never be hard-coded; they arrive "
                    "as environment variables. Static files such as CSS and "
                    "images have to be collected and served efficiently. And the "
                    "process that starts your app must also apply database "
                    "migrations, otherwise new code meets an old schema. Hosting "
                    "choices range from a virtual private server you manage "
                    "yourself to platforms such as Railway or Render that build "
                    "and run your code straight from a Git repository. For a "
                    "learning project, a platform is the fastest route to a "
                    "working URL.\n\n"
                    "Key takeaway: deployment runs the same code in a stricter "
                    "environment, configured entirely through environment "
                    "variables."
                ),
            },
            {
                "title": "Deploying a Django App to the Cloud",
                "content": (
                    "A typical Django deployment on a platform such as Railway "
                    "follows the same short sequence.\n\n"
                    "First, prepare the project: turn debug off, restrict the "
                    "allowed hosts, read every secret from the environment, add a "
                    "production web server such as Gunicorn, and make sure static "
                    "files are collected. Second, commit everything to Git and "
                    "connect the repository to the platform. Third, add a "
                    "database plugin and the environment variables the app "
                    "expects - the secret key, the database URL and any "
                    "third-party API keys. Fourth, define the start command that "
                    "runs migrations and then starts the web server.\n\n"
                    "Two details cause most beginner failures. The first is "
                    "HTTPS: the platform ends encryption at its proxy and "
                    "forwards the original scheme in a header, so the framework "
                    "must be told to trust it, otherwise secure cookies and "
                    "redirects break. The second is host checking: the deployed "
                    "domain must be listed as allowed, and form security must "
                    "trust that origin. Reading the deploy logs carefully usually "
                    "reveals both immediately.\n\n"
                    "Key takeaway: deploy with environment variables, a "
                    "production server, migrations in the start command, and the "
                    "proxy and host settings correct."
                ),
            },
            {
                "title": "Going Live: Secrets, Debugging and Maintenance",
                "content": (
                    "Deployment is not a one-off event; a live application needs "
                    "regular care.\n\n"
                    "Secrets management comes first. Keep keys out of the "
                    "repository, store them only in the platform's variable "
                    "settings, and rotate anything that has been exposed. Keep "
                    "debug mode off in production so internal details are never "
                    "shown to visitors, and make sure error logs are collected "
                    "somewhere you actually read. When something breaks, the "
                    "fastest path is usually the platform's log view: reproduce "
                    "the failing action and watch the traceback appear.\n\n"
                    "Then think about the data. Schedule and verify regular "
                    "database backups, and test restoring them at least once. "
                    "Plan how you will ship updates: a small change, a migration "
                    "if needed, a deploy, and a check that the site still works. "
                    "Add monitoring or at least an uptime check so you learn "
                    "about outages before your users do, and keep an eye on cost "
                    "and usage so a surprise bill does not end the project. "
                    "Finally, treat security as routine: keep dependencies "
                    "updated, serve everything over HTTPS, and protect the admin "
                    "area.\n\n"
                    "Key takeaway: production needs secrets kept safe, logs "
                    "read, backups tested and updates shipped deliberately."
                ),
            },
        ],
    },
]


class Command(BaseCommand):
    help = (
        "Add the extra courses (Computer Networks, Programming Fundamentals, "
        "RESTful API, Software Engineering, Project Management, Artificial "
        "Intelligence, Machine Learning, Deployment) and their lessons. "
        "Safe to re-run: existing records are never duplicated or modified."
    )

    def handle(self, *args, **options):
        courses_created = 0
        lessons_created = 0

        for course_data in COURSES:
            course, course_created = Course.objects.get_or_create(
                title=course_data["title"],
                defaults={
                    "description": course_data["description"],
                    "price": Decimal(course_data["price"]),
                    "is_published": True,
                },
            )
            courses_created += 1 if course_created else 0

            for position, lesson_data in enumerate(course_data["lessons"], start=1):
                _, lesson_created = Lesson.objects.get_or_create(
                    course=course,
                    order=position,
                    defaults={
                        "title": lesson_data["title"],
                        "content": lesson_data["content"],
                    },
                )
                lessons_created += 1 if lesson_created else 0

            status = "created" if course_created else "already exists"
            self.stdout.write(f"  {status}: {course.title}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Courses created: {courses_created}, "
                f"lessons created: {lessons_created}. "
                f"Total courses: {Course.objects.count()}, "
                f"total lessons: {Lesson.objects.count()}."
            )
        )
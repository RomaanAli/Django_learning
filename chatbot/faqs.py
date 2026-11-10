"""
Curated public help FAQs for the E-Learning RAG chatbot.

Every fact, button label, and URL below is checked against the real views,
templates, and urls.py in this project. Keep this file free of admin
details, private user data, unpublished content, and enrollment numbers.

Each entry: "title", "content", and "source_url" (only a real public page).
"""

FAQS = [
    {
        "title": "What can a student do on E_learning?",
        "content": (
            "A student can do the following on E_learning:\n"
            "- Browse all published courses on the courses page at /courses/.\n"
            "- Enroll in a free course with the 'Enroll for free' button on the course page.\n"
            "- Buy a paid course and pay securely with Stripe from the course page.\n"
            "- Read the lessons of a course after enrolling in it. Lessons are shown on the course page (/courses/<id>/).\n"
            "- See all enrolled courses under 'Your Enrolled Courses' on the student dashboard at /accounts/dashboard/.\n"
            "- View and edit their profile at /accounts/profile/.\n"
            "- Apply to become an instructor with the 'Apply to Teach' button on the profile page."
        ),
        "source_url": "/accounts/dashboard/",
    },
    {
        "title": "What can an instructor do on E_learning?",
        "content": (
            "An approved instructor can do the following on E_learning:\n"
            "- Create a new course. A new course is saved as a draft first.\n"
            "- Set and edit the course title, description, and price.\n"
            "- Add lessons to a course, set the lesson order, and edit or delete lessons.\n"
            "- Publish a course so students can see it, or unpublish it again.\n"
            "- Manage their courses from the instructor dashboard at /accounts/instructor/dashboard/ "
            "and from the instructor course list at /courses/instructor/.\n"
            "An instructor account must be approved before it can create courses. "
            "Instructors cannot enroll in or buy courses."
        ),
        "source_url": "/accounts/instructor/dashboard/",
    },
    {
        "title": "How do I register on E_learning?",
        "content": (
            "To register, go to the register page at /accounts/register/.\n"
            "1. Choose Student or Instructor at the top of the form.\n"
            "2. Fill in your details: username, name, email, and password. "
            "If you choose Instructor, you must also upload a document that shows you can teach "
            "(PDF, PNG, or JPG, up to 5 MB).\n"
            "3. A 6-digit verification code is sent to your email. Enter it on the verify email page to activate your account.\n"
            "4. After that, log in on the login page.\n"
            "Students can also sign up with the 'Continue with Google' button. "
            "This button is shown only for Student registration.\n"
            "An instructor account must be approved before it can create courses."
        ),
        "source_url": "/accounts/register/",
    },
    {
        "title": "How do I log in?",
        "content": (
            "Go to the login page at /accounts/login/. Enter your username or email and your password, "
            "then log in. You can also use the 'Continue with Google' button.\n"
            "There is one shared login page for students and instructors. "
            "There is no separate student login page or instructor login page.\n"
            "After login, students go to the student dashboard (/accounts/dashboard/) and "
            "instructors go to the instructor dashboard (/accounts/instructor/dashboard/).\n"
            "If your email is not verified yet, use the 'Resend code' link on the login page to get a new verification code."
        ),
        "source_url": "/accounts/login/",
    },
    {
        "title": "How do I enroll in a course?",
        "content": (
            "You need to be logged in as a student to enroll. First open a published course from the courses page at /courses/.\n"
            "Free course: on the course page, click 'Enroll for free'. You are enrolled right away.\n"
            "Paid course: on the course page, click 'Buy this course'. You are taken to a confirm page and then to "
            "the secure Stripe payment page. After the payment succeeds, you are enrolled.\n"
            "After enrollment, the course appears under 'Your Enrolled Courses' on your dashboard at /accounts/dashboard/, "
            "and its lessons are unlocked on the course page.\n"
            "Instructors cannot enroll in or buy courses."
        ),
        "source_url": "/courses/",
    },
    {
        "title": "How do I find a course and open its lessons?",
        "content": (
            "Open the courses page at /courses/ to see all published courses. "
            "Click a course to open its course page (/courses/<id>/). The course page shows the description, "
            "the price, and how many lessons the course has.\n"
            "The lesson content is shown on the course page only after you enroll in that course. "
            "Before you enroll, the page tells you to enroll in the course to unlock the lessons.\n"
            "You can also open your enrolled courses from your dashboard at /accounts/dashboard/."
        ),
        "source_url": "/courses/",
    },
    {
        "title": "How do I change my role from student to instructor?",
        "content": (
            "There is no change-role button in settings or in the profile.\n"
            "To become an instructor, a logged-in student applies like this:\n"
            "1. Open your profile page at /accounts/profile/ and click 'Apply to Teach', "
            "or go directly to the instructor apply page at /accounts/instructor/apply/.\n"
            "2. Upload your verification document, such as a certificate or degree (PDF, PNG, or JPG, up to 5 MB).\n"
            "3. Wait for approval. Your document stays pending until it is reviewed.\n"
            "After approval, your student account becomes an instructor account and you can create courses.\n"
            "Admin is not a role you can choose, and you cannot change your own role to admin."
        ),
        "source_url": "/accounts/instructor/apply/",
    },
]

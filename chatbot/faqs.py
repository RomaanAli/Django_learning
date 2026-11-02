"""
Curated FAQs and platform guide for the E-Learning RAG chatbot.
All facts, URLs, and workflows are verified against the real codebase.
"""

FAQS = [
    {
        "title": "How to register as a student or instructor",
        "content": (
            "To register on the platform, visit /accounts/register/. "
            "You can choose your role using the Student or Instructor toggle. "
            "For Student registration, enter your username, email, and password. "
            "After submitting the form, an OTP (one-time verification code) will be emailed to you. "
            "Enter the OTP at /accounts/verify-email/ to activate your account. "
            "You can also use 'Continue with Google' to sign up directly with your Google account. "
            "For Instructor registration, you provide your credentials and upload your verification document. "
            "Instructor accounts require admin approval before you can start publishing courses."
        ),
        "source_url": "/accounts/register/",
    },
    {
        "title": "How to log in on the shared login page",
        "content": (
            "To log in, visit the shared login page at /accounts/login/. "
            "You can sign in using either your username or your registered email address along with your password. "
            "Alternatively, you can click 'Continue with Google' to sign in with your connected Google account. "
            "Once logged in, students are redirected to the student dashboard at /accounts/dashboard/, "
            "and instructors have access to both their dashboard and the instructor portal."
        ),
        "source_url": "/accounts/login/",
    },
    {
        "title": "Instructor document upload and admin approval process",
        "content": (
            "Anyone registering as an instructor must submit a verification document (such as a CV, degree, or certificate). "
            "If you registered without uploading or need to update your document, visit /accounts/instructor/upload-document/ "
            "or /accounts/instructor/apply/. "
            "After uploading, your account status is set to pending approval. "
            "A platform administrator reviews the submission in the Django Admin. "
            "Once approved, your instructor privileges are activated (can_teach=True), allowing you to create, edit, "
            "and publish courses from /courses/instructor/ and manage them at /accounts/instructor/dashboard/."
        ),
        "source_url": "/accounts/instructor/dashboard/",
    },
    {
        "title": "How to enroll in a free course",
        "content": (
            "To enroll in a free course: "
            "1. Browse available courses at /courses/. "
            "2. Click on any course listed with a price of $0.00 to open its detail page (/courses/<id>/). "
            "3. Click the 'Enroll for Free' button. "
            "You will be instantly enrolled without entering payment information, "
            "and the course will appear on your dashboard at /accounts/dashboard/ with immediate access to all lessons."
        ),
        "source_url": "/courses/",
    },
    {
        "title": "How to pay for a paid course through Stripe",
        "content": (
            "To purchase and enroll in a paid course: "
            "1. Visit the course catalog at /courses/ and select the paid course. "
            "2. On the course detail page (/courses/<id>/), click the 'Enroll' or 'Buy Now' button. "
            "3. You will be redirected to the secure Stripe Checkout session (/payments/checkout/<course_id>/). "
            "4. Enter your card details and complete payment on Stripe's secure page. "
            "5. Once payment succeeds, Stripe notifies our system via a webhook, your enrollment is automatically confirmed, "
            "and you are redirected to the confirmation page at /payments/success/<course_id>/."
        ),
        "source_url": "/courses/",
    },
    {
        "title": "Where to find courses and lessons",
        "content": (
            "The full catalog of published courses is located at /courses/. "
            "Each course card displays the title, instructor name, and price. "
            "Clicking on a course opens its detail page (/courses/<id>/), where you can view the full course description "
            "and the list of curriculum lessons. "
            "Once enrolled, you can click on any lesson to read its content. "
            "You can also see all courses you are currently enrolled in by visiting your dashboard at /accounts/dashboard/."
        ),
        "source_url": "/courses/",
    },
    {
        "title": "Email verification and OTP troubleshooting",
        "content": (
            "When registering with email and password, an OTP verification code is sent to your email. "
            "Enter this 6-digit code on the verification screen at /accounts/verify-email/. "
            "If you did not receive the OTP email, check your spam or junk folder, "
            "or click 'Resend OTP' at /accounts/resend-otp/ to get a new code. "
            "The OTP expires after a short period for security."
        ),
        "source_url": "/accounts/verify-email/",
    },
]


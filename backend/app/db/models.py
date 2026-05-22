"""Hamma modellarni bir joydan import qilish — Alembic autogenerate uchun.

Yangi modul qo'shilganda, uning models.py ni shu yerda import qilish kerak.
"""

# ruff: noqa: F401
# IZOH: import tartibi muhim — FK referenced jadvallar oldin import qilinishi kerak.
from app.modules.organizations.models import Organization
from app.modules.users.models import Profile, User
from app.modules.rbac.models import Permission, Role, RolePermission, UserRole
from app.modules.auth.models import (
    AuditLog,
    BackupCode,
    EmailVerificationToken,
    LoginAttempt,
    PasswordResetToken,
    UserSession,
)
from app.modules.academic.models import (
    AcademicCalendar,
    AcademicGroup,
    AcademicSemester,
    Curriculum,
    CurriculumSubject,
    Department,
    Faculty,
    HemisClassifier,
    Specialty,
    Subject,
    SubjectPrerequisite,
)
from app.modules.communications.models import (
    Conversation,
    ConversationMember,
    ForumPost,
    ForumPostLike,
    ForumThread,
    LessonComment,
    LessonCommentLike,
    Message,
)
from app.modules.content.models import ContentItem
from app.modules.scorm.models import ScormAttempt, ScormPackage
from app.modules.courses.models import (
    Course,
    Enrollment,
    Lesson,
    LessonProgress,
    Module,
)
from app.modules.assignments.models import (
    Assignment,
    GradeAppeal,
    PeerReview,
    Rubric,
    Submission,
)
from app.modules.live.models import LiveAttendance, LiveCaption, LiveRecording, LiveSession
from app.modules.exams.models import (
    Answer,
    CodeTestCase,
    Exam,
    ExamAttempt,
    IdReferencePhoto,
    ProctoringEvent,
    ProctoringSnapshot,
    Question,
    QuestionOption,
)
from app.integrations.hemis.models import HemisSyncLog
from app.modules.notifications.models import Notification
from app.modules.certificates.models import Certificate
from app.modules.gamification.models import (
    Badge,
    GamificationEvent,
    UserBadge,
    UserPoints,
)

from fastapi import APIRouter

from app.api.v1 import (
    academic,
    assignments,
    auth,
    certificates,
    communications,
    content,
    courses,
    exams,
    gamification,
    health,
    hemis_tutor,
    live_sessions,
    notifications,
    rbac,
    scorm,
    users,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(rbac.router, tags=["rbac"])
api_router.include_router(academic.router, tags=["academic"])
api_router.include_router(content.router)
api_router.include_router(courses.router, tags=["courses"])
api_router.include_router(assignments.router, tags=["assignments"])
api_router.include_router(live_sessions.router, tags=["live"])
api_router.include_router(exams.router, tags=["exams"])
api_router.include_router(notifications.router, tags=["notifications"])
api_router.include_router(hemis_tutor.router)
api_router.include_router(scorm.router)
api_router.include_router(communications.router)
api_router.include_router(certificates.router)
api_router.include_router(gamification.router)

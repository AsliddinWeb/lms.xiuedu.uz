"""HEMIS mock data — Phase 10c.

Dev/test environment'ida `settings.HEMIS_MODE = 'mock'` bo'lganda
`HemisClient` ushbu modul'dan deterministik fixtura JSON qaytaradi.

Data OpenAPI spec example'lari va HEMIS realistic strukturasiga asoslangan.

Production'da `HEMIS_MODE='real'` qilib mock'ni o'chiriladi.
"""

from __future__ import annotations

from typing import Any


# ============================================================================
# Auth
# ============================================================================

MOCK_STUDENT_TOKEN = (
    "mock.student.token.eyJzdWIiOiI5OTkyMTExMDAwNzMiLCJ0eXAiOiJzdHVkZW50In0"
)

MOCK_TUTOR_TOKEN = (
    "mock.tutor.token.eyJzdWIiOiJ0dXRvcl9sb2dpbiIsInR5cCI6InR1dG9yIn0"
)


def mock_student_login(login: str, password: str) -> dict[str, Any]:
    """Phase 10c — mock student login.

    Login `999*` bilan boshlansa muvaffaqiyatli; password kamida 6 belgi bo'lishi kerak.
    """
    if not login.startswith("999"):
        return {"success": False, "error": "Login topilmadi", "code": 401}
    if len(password) < 6:
        return {"success": False, "error": "Parol noto'g'ri", "code": 401}
    return {
        "success": True,
        "error": None,
        "code": 200,
        "data": {"token": MOCK_STUDENT_TOKEN},
    }


def mock_tutor_login(login: str, password: str, recaptcha: str) -> dict[str, Any]:
    if not login or not password or not recaptcha:
        return {"success": False, "error": "Maydonlar to'ldirilishi shart", "code": 400}
    if login == "wrong":
        return {"success": False, "error": "Login yoki parol noto'g'ri", "code": 401}
    return {
        "success": True,
        "code": 200,
        "data": {
            "token": MOCK_TUTOR_TOKEN,
            "refresh_token": "mock-refresh-" + login,
        },
    }


# ============================================================================
# Student profile
# ============================================================================

def mock_account_me(token: str) -> dict[str, Any]:
    """Phase 10c — `GET /v1/account/me` mock.

    Token tarkibida `student` yoki `sso.lms` bo'lsa standart talaba ma'lumotlari
    qaytariladi. Phase 10e da SSO token ham qabul qilinadi.
    """
    if "student" not in token and "sso.lms" not in token:
        return {"success": False, "error": "Token yaroqsiz", "code": 401}
    return {
        "success": True,
        "code": 200,
        "data": {
            "id": 999001,
            "student_id_number": "999211100073",
            "passport_pin": "12345678901234",
            "first_name": "Asadbek",
            "second_name": "Rasulov",
            "third_name": "Anvarovich",
            "full_name": "Asadbek Rasulov Anvarovich",
            "short_name": "A.Rasulov",
            "university": "Xalqaro Innovatsiya Universiteti",
            "universityOwnership": {"code": "private", "name": "Xususiy"},
            "image": "https://student.xiuedu.uz/avatars/999001.jpg",
            "birth_date": 946684800,  # 2000-01-01
            "email": None,
            "group": {
                "id": 5001,
                "name": "ATM-21-1",
                "educationLang": {"code": "uz", "name": "O'zbek"},
            },
            "faculty": {"id": 11, "code": "ATM", "name": "Axborot Texnologiyalari va Matematika", "active": True},
            "educationLang": {"code": "uz", "name": "O'zbek"},
            "semester": {
                "id": 7,
                "code": "7",
                "name": "7-semestr",
                "current": True,
                "education_year": {"code": "2026-2027", "name": "2026-2027", "current": True},
            },
            "specialty": {"code": "60611100", "name": "Kompyuter ilmlari"},
            "level": {"code": "bachelor", "name": "Bakalavr"},
            "educationForm": {"code": "full_time", "name": "Kunduzgi"},
            "educationType": {"code": "regular", "name": "Standart"},
            "paymentForm": {"code": "contract", "name": "Shartnoma"},
            "studentStatus": {"code": "active", "name": "Talaba"},
            "country": {"code": "UZ", "name": "O'zbekiston"},
            "province": {"code": "10", "name": "Toshkent shahri"},
            "district": {"code": "1004", "name": "Yashnobod tumani"},
            "address": "Toshkent shahri, Yashnobod tumani, Bunyodkor 1-uy",
            "socialCategory": {"code": "general", "name": "Umumiy"},
            "validateUrl": "https://student.xiuedu.uz/validate/999001",
            "hash": "abc123def456",
        },
    }


# ============================================================================
# Education endpoints
# ============================================================================

def mock_subject_list(token: str, semester: int | None = None) -> dict[str, Any]:
    return {
        "success": True,
        "code": 200,
        "data": [
            {
                "id": 1001,
                "curriculumSubject": {
                    "id": 2001,
                    "subject": {"code": "CS101", "name": "Algoritmlar va ma'lumotlar tuzilmasi"},
                    "credit": 4,
                    "totalAcload": 120,
                },
                "semester": {"id": semester or 7, "name": f"{semester or 7}-semestr"},
                "currentGrade": {"code": "85", "name": "85"},
                "totalGrade": "85",
                "rating": "A",
            },
            {
                "id": 1002,
                "curriculumSubject": {
                    "id": 2002,
                    "subject": {"code": "MTH201", "name": "Matematik tahlil"},
                    "credit": 3,
                    "totalAcload": 90,
                },
                "semester": {"id": semester or 7, "name": f"{semester or 7}-semestr"},
                "currentGrade": {"code": "78", "name": "78"},
                "totalGrade": "78",
                "rating": "B",
            },
        ],
    }


def mock_schedule(token: str) -> dict[str, Any]:
    return {
        "success": True,
        "code": 200,
        "data": [
            {
                "id": 5001,
                "subject": {"code": "CS101", "name": "Algoritmlar"},
                "employee": {"id": 7001, "name": "Karimov Bobur"},
                "auditorium": {"id": 301, "name": "301-xona"},
                "lessonPair": {"code": "2", "name": "2-juftlik", "start_time": "10:00", "end_time": "11:20"},
                "weekday": 2,
                "lesson_date": 1684627200,  # mock unix
            }
        ],
    }


def mock_gpa_list(token: str) -> dict[str, Any]:
    return {
        "success": True,
        "code": 200,
        "data": [
            {"semester": {"id": 6, "name": "6-semestr"}, "gpa": "3.85", "credits": 30},
            {"semester": {"id": 7, "name": "7-semestr"}, "gpa": "3.92", "credits": 28},
        ],
    }


def mock_attendance(token: str, semester: int | None = None) -> dict[str, Any]:
    return {
        "success": True,
        "code": 200,
        "data": [
            {
                "date": 1684627200,
                "subject": {"code": "CS101", "name": "Algoritmlar"},
                "type": "attended",  # 'attended' | 'absent' | 'late'
                "lesson_pair": "2",
            }
        ],
    }


def mock_exam_table(token: str) -> dict[str, Any]:
    return {
        "success": True,
        "code": 200,
        "data": [
            {
                "id": 9001,
                "subject": {"code": "CS101", "name": "Algoritmlar"},
                "exam_date": 1684627200,
                "auditorium": {"id": 301, "name": "301-xona"},
                "status": "upcoming",
            }
        ],
    }


def mock_semesters(token: str) -> dict[str, Any]:
    return {
        "success": True,
        "code": 200,
        "data": [
            {"id": 1, "code": "1", "name": "1-semestr", "current": False},
            {"id": 7, "code": "7", "name": "7-semestr", "current": True},
        ],
    }


# ============================================================================
# Backend API (admin sync)
# ============================================================================

def mock_student_list(token: str, page: int = 1, limit: int = 100) -> dict[str, Any]:
    """Backend API — barcha talabalar (paginatsiya)."""
    return {
        "success": True,
        "code": 200,
        "data": {
            "items": [mock_account_me("student")["data"]],
            "pagination": {"page": page, "limit": limit, "total": 1, "pageCount": 1},
        },
    }


def mock_employee_list(token: str, page: int = 1, limit: int = 100, type_: str = "employee") -> dict[str, Any]:
    return {
        "success": True,
        "code": 200,
        "data": {
            "items": [
                {
                    "id": 7001,
                    "name": "Karimov Bobur Anvarovich",
                    "first_name": "Bobur",
                    "second_name": "Karimov",
                    "third_name": "Anvarovich",
                    "passport_pin": "98765432109876",
                    "email": "b.karimov@xiuedu.uz",
                    "phone": "+998901112233",
                    "gender": "M",
                    "department": {"id": 11, "code": "ATM", "name": "Axborot Texnologiyalari va Matematika"},
                    "staffPosition": {"code": "teacher", "name": "O'qituvchi"},
                    "employmentForm": {"code": "primary", "name": "Asosiy"},
                    "employmentStaff": {"code": "1.0", "name": "1.0 stavka"},
                    "academicDegree": {"code": "phd", "name": "PhD"},
                    "academicTitle": {"code": "dotsent", "name": "Dotsent"},
                }
            ],
            "pagination": {"page": page, "limit": limit, "total": 1, "pageCount": 1},
        },
    }


def mock_department_list(token: str) -> dict[str, Any]:
    return {
        "success": True,
        "code": 200,
        "data": [
            {
                "id": 11,
                "code": "ATM",
                "name": "Axborot Texnologiyalari va Matematika",
                "parent": 1,
                "active": True,
                "structureType": {"code": "faculty", "name": "Fakultet"},
                "localityType": {"code": "city", "name": "Shahar"},
            }
        ],
    }


def mock_group_list(token: str) -> dict[str, Any]:
    return {
        "success": True,
        "code": 200,
        "data": [
            {
                "id": 5001,
                "name": "ATM-21-1",
                "educationLang": {"code": "uz", "name": "O'zbek"},
                "department": 11,
                "specialty": "60611100",
            }
        ],
    }


def mock_curriculum_list(token: str) -> dict[str, Any]:
    return {
        "success": True,
        "code": 200,
        "data": [
            {
                "id": 3001,
                "name": "Kompyuter ilmlari (2026)",
                "specialty": {"code": "60611100", "name": "Kompyuter ilmlari"},
                "validFrom": "2026-09-01",
                "totalCredits": 240,
            }
        ],
    }


# ============================================================================
# SSO
# ============================================================================

def mock_sso_targets(token: str) -> dict[str, Any]:
    return {
        "success": True,
        "code": 200,
        "data": [
            {"code": "lms", "name": "XIU LMS", "description": "Masofaviy ta'lim platformasi"},
            {"code": "career", "name": "Career.edu.uz", "description": "Karyera markazi"},
        ],
    }


def mock_sso_redirect_url(token: str, target: str) -> dict[str, Any]:
    if "student" not in token:
        return {"success": False, "error": "Token yaroqsiz", "code": 401}
    if target not in {"lms", "career"}:
        return {"success": False, "error": f"Target topilmadi: {target}", "code": 400}
    return {
        "success": True,
        "code": 200,
        "data": {
            "redirect_url": f"https://lms.xiuedu.uz/auth/sso/callback?sso_token=mock.sso.{target}.{MOCK_STUDENT_TOKEN[-20:]}",
            "target": target,
            "expires_in": 300,
        },
    }


# ============================================================================
# Tutor API
# ============================================================================

def mock_tutor_profile(token: str) -> dict[str, Any]:
    if "tutor" not in token:
        return {"success": False, "error": "Token yaroqsiz", "code": 401}
    return {
        "success": True,
        "code": 200,
        "data": {
            "id": 7001,
            "name": "Karimov Bobur Anvarovich",
            "department": {"code": "ATM", "name": "ATM Fakulteti"},
            "academicDegree": {"code": "phd", "name": "PhD"},
        },
    }


def mock_tutor_groups(token: str) -> dict[str, Any]:
    return {
        "success": True,
        "code": 200,
        "data": [
            {"id": 5001, "name": "ATM-21-1", "studentsCount": 25},
            {"id": 5002, "name": "ATM-21-2", "studentsCount": 22},
        ],
    }


def mock_tutor_group_students(token: str, group_id: int) -> dict[str, Any]:
    return {
        "success": True,
        "code": 200,
        "data": [
            {"id": 999001, "student_id_number": "999211100073", "full_name": "Asadbek Rasulov"},
            {"id": 999002, "student_id_number": "999211100074", "full_name": "Bekzod Aliyev"},
        ],
    }


def mock_tutor_grade_gpa(token: str, group_id: int) -> dict[str, Any]:
    """`/ver1/tutor/grade/gpa` — guruh GPA reytingi."""
    if "tutor" not in token:
        return {"success": False, "error": "Token yaroqsiz", "code": 401}
    return {
        "success": True,
        "code": 200,
        "data": [
            {
                "student_id": 999001,
                "full_name": "Asadbek Rasulov",
                "gpa": "3.92",
                "credits": 28,
                "rank": 1,
            },
            {
                "student_id": 999002,
                "full_name": "Bekzod Aliyev",
                "gpa": "3.71",
                "credits": 28,
                "rank": 2,
            },
        ],
    }


def mock_tutor_attendance_by_subject(
    token: str, group_id: int, subject_id: int | None = None
) -> dict[str, Any]:
    """`/ver1/tutor/attendance/by-subject` — fan bo'yicha guruh davomati."""
    if "tutor" not in token:
        return {"success": False, "error": "Token yaroqsiz", "code": 401}
    return {
        "success": True,
        "code": 200,
        "data": [
            {
                "student_id": 999001,
                "full_name": "Asadbek Rasulov",
                "subject": {"code": "CS101", "name": "Algoritmlar"},
                "total_lessons": 30,
                "attended": 28,
                "absent": 2,
                "attendance_percent": "93.33",
            },
            {
                "student_id": 999002,
                "full_name": "Bekzod Aliyev",
                "subject": {"code": "CS101", "name": "Algoritmlar"},
                "total_lessons": 30,
                "attended": 25,
                "absent": 5,
                "attendance_percent": "83.33",
            },
        ],
    }


def mock_tutor_grade_debtors(token: str, group_id: int) -> dict[str, Any]:
    """`/ver1/tutor/grade/debtors` — qarzdor talabalar."""
    if "tutor" not in token:
        return {"success": False, "error": "Token yaroqsiz", "code": 401}
    return {
        "success": True,
        "code": 200,
        "data": [
            {
                "student_id": 999003,
                "full_name": "Davron Toshev",
                "debt_count": 2,
                "subjects": [
                    {"code": "MTH201", "name": "Matematik tahlil"},
                    {"code": "CS101", "name": "Algoritmlar"},
                ],
            }
        ],
    }

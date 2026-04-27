import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "survey_results")

BOOL_YES = {"да", "yes"}

INTERESTS_MAP = {
    "Природа": "nature",
    "Технологии": "tech",
    "Спорт": "sport",
    "Искусство": "art",
    "Архитектура": "architecture",
}

FORMAT_MAP = {
    "Классический": "classic",
    "Игровой": "game",
    "Интерактивный": "interactive",
}

SCHEME_MAP = {
    "Светлая": "light",
    "Тёмная": "dark",
}

DISEASE_VALUE_MAP = {
    "Миопия (близорукость)": "myopia",
    "Гиперметропия (дальнозоркость)": "hyperopia",
    "Нет диагноза": "Healthy",
}

BL_TYPE = {
    "Здоровый": "Healthy",
    "Нет": "Healthy",
    "Дейтеранопия (слабость к зелёному)": "Deuteranopia",
    "Deuteranopia": "Deuteranopia",
    "Протанопия (слабость к красному)": "Protanopia",
    "Protanopia": "Protanopia",
    "Тританопия (слабость к синему)": "Tritanopia",
    "Tritanopia": "Tritanopia",
    "Ахроматопсия (нет цветного зрения)": "Achromatopsia",
    "Achromatopsia": "Achromatopsia",
}

LEVEL_VALUE_MAP = {
    # Russian text options
    "Слабая (-1)": "-1",
    "Слабая (-2)": "-2",
    "Средняя (-3)": "-3",
    "Средняя (-4)": "-4",
    "Высокая (-5)": "-5",
    "Высокая (-6)": "-6",
    "Слабая (+1)": "+1",
    "Слабая (+2)": "+2",
    "Средняя (+3)": "+3",
    "Средняя (+4)": "+4",
    "Высокая (+5)": "+5",
    "Высокая (+6)": "+6",
    "Не знаю": "unknown",
    # Direct numeric values (from survey answers)
    "-1": "-1",
    "-2": "-2",
    "-3": "-3",
    "-4": "-4",
    "-5": "-5",
    "-6": "-6",
    "+1": "+1",
    "+2": "+2",
    "+3": "+3",
    "+4": "+4",
    "+5": "+5",
    "+6": "+6",
}


@dataclass
class SurveyAnswer:
    question_id: str
    question_text: str
    answer: list


@dataclass
class SurveyResult:
    survey_id: str  = ""
    answers: list = field(default_factory=list)
    completed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class UserProfile:
    user_id: Optional[int] = None
    name: str = ""
    age: Optional[int] = None
    has_vision_problems: bool = False
    wears_glasses: bool = False
    bl_type: str = "Healthy"
    disease_type: str = "Healthy"
    disease_level: str = "0"
    interests: list = field(default_factory=list)
    training_format: str = ""
    color_scheme: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


class ResultProcessor:
    def process(self, result: SurveyResult) -> dict:
        """Process survey result: build profile, generate plan, save to JSON."""
        profile = self._build_profile(result)
        plan = self._build_plan(profile, result)
        summary = self._make_summary(profile, plan)
        
        # Save everything to JSON file
        json_path = self._save_to_json(profile, result, plan)
        
        # Generate user_id from JSON filename (timestamp-based, unique identifier)
        user_id = self._generate_user_id_from_path(json_path) if json_path else None

        return {
            "status": "ok",
            "user_id": user_id,
            "profile_name": profile.name,
            "profile_age": str(profile.age) if profile.age else "—",
            "profile_disease": f"{profile.disease_type} {profile.disease_level}",
            "profile_bl": profile.bl_type,
            "exercise_plan": plan,
            "summary": summary,
            "json_path": json_path,
        }

    def _build_profile(self, result: SurveyResult) -> UserProfile:
        profile = UserProfile()
        for ans in result.answers:
            qid = ans.question_id
            values = ans.answer

            if qid == "q_name":
                profile.name = values[0].strip() if values else ""
            elif qid == "q_age":
                try:
                    profile.age = int(values[0]) if values else None
                except ValueError:
                    profile.age = None
            elif qid == "q_med_001":
                profile.has_vision_problems = self._to_bool(values)
            elif qid == "q_med_002":
                profile.wears_glasses = self._to_bool(values)
            elif qid == "q_disease_type":
                v = values[0] if values else ""
                profile.disease_type = DISEASE_VALUE_MAP.get(v, v.lower())
            elif qid == "q_disease_level":
                v = values[0] if values else ""
                profile.disease_level = LEVEL_VALUE_MAP.get(v, v if v else profile.disease_level)
            elif qid == "q_color_blindness":
                v = values[0] if values else ""
                profile.bl_type = BL_TYPE.get(v, profile.bl_type)
            elif qid == "q_int_001":
                profile.interests = [ INTERESTS_MAP.get(v, v.lower()) for v in values ]
            elif qid == "q_pref_001":
                v = values[0] if values else ""
                profile.training_format = FORMAT_MAP.get(v, v.lower())
            elif qid == "q_pref_002":
                v = values[0] if values else ""
                profile.color_scheme = SCHEME_MAP.get(v, v.lower())
        return profile

    @staticmethod
    def _to_bool(values: list) -> bool:
        return bool(values) and values[0].strip().lower() in BOOL_YES

    def _build_plan(self, profile: UserProfile, result: SurveyResult) -> dict:
        try:
            from utils.plan_builder import PlanBuilder
            answers_dict = {
                ans.question_id: ans.answer
                for ans in result.answers
            }
            answers_dict["q_disease_type"] = [profile.disease_type]
            answers_dict["q_disease_level"] = [profile.disease_level]
            builder = PlanBuilder()
            plan = builder.build(profile.user_id, answers_dict)
            plan.bl_type = profile.bl_type  # Set colorblindness type from profile
            return plan.to_dict()
        except Exception as e:
            print(f"[PlanBuilder] ошибка: {e}", file=sys.stderr)
            return self._fallback_plan(profile)

    @staticmethod
    def _fallback_plan(profile: UserProfile) -> dict:
        return {
            "disease": profile.disease_type,
            "level": profile.disease_level,
            "bl_type": profile.bl_type,
            "background": "plain_white.png",
            "object_hex": "#FFFFFF",
            "object_scale": 1.0,
            "speed_ms": 30,
            "exercises": [
                {"name": "circle_right", "speed": "medium"},
                {"name": "horizontal",   "speed": "medium"},
            ],
            "notes": ["Стандартная программа"],
        }

    def _save_to_json(self, profile: UserProfile, result: SurveyResult, plan: dict):
        """Save complete user profile, survey answers, and exercise plan to JSON."""
        try:
            os.makedirs(RESULTS_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S%f")[:-3]  # Include milliseconds
            name_slug = profile.name.replace(" ", "_") or "user"
            filename = f"{name_slug}_{timestamp}.json"
            path = os.path.join(RESULTS_DIR, filename)

            data = {
                "survey_id": result.survey_id,
                "completed_at": result.completed_at.isoformat(),
                "profile": {
                    "name": profile.name,
                    "age": profile.age,
                    "has_vision_problems": profile.has_vision_problems,
                    "bl_type": profile.bl_type,
                    "wears_glasses": profile.wears_glasses,
                    "disease_type": profile.disease_type,
                    "disease_level": profile.disease_level,
                    "interests": profile.interests,
                    "training_format": profile.training_format,
                    "color_scheme": profile.color_scheme,
                },
                "exercise_plan": plan,
                "answers": [
                    {
                        "question_id": a.question_id,
                        "question_text": a.question_text,
                        "answer": a.answer,
                    }
                    for a in result.answers
                ],
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[ResultProcessor] Профиль сохранен: {path}", file=sys.stderr)
            return path
        except Exception as e:
            print(f"[ResultProcessor] Ошибка при сохранении JSON: {e}", file=sys.stderr)
            return None

    @staticmethod
    def _make_summary(profile: UserProfile, plan: dict) -> str:
        """Generate a human-readable summary of the profile and plan."""
        lines = []
        if profile.name:
            lines.append(f"Пользователь: {profile.name}" + (f", {profile.age} лет" if profile.age else ""))
        lines.append(f"Диагноз: {profile.disease_type} {profile.disease_level}" + (f", {profile.bl_type}" if profile.bl_type!="Healthy" else ""))
        lines.append(f"Очки/линзы: {'Да' if profile.wears_glasses else 'Нет'}")
        if profile.interests:
            lines.append(f"Интересы: {', '.join(profile.interests)}")
        lines.append("─" * 30)
        for note in plan.get("notes", []):
            lines.append(f"• {note}")
        lines.append(f"Фон: {plan.get('background', '—')}")
        return "\n".join(lines)
    
    @staticmethod
    def _generate_user_id_from_path(json_path: str) -> str:
        """Generate a unique user_id from the JSON file path."""
        try:
            if not json_path:
                return None
            # Use the filename (without extension) as the ID
            filename = os.path.basename(json_path)
            user_id = os.path.splitext(filename)[0]
            return user_id
        except Exception:
            return None

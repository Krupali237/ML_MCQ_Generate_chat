from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class QuizResult:
    score: int
    total: int
    percentage: float
    details: List[Dict[str, Any]]


class QuizManager:
    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self.questions: List[Dict[str, Any]] = []
        self.current_index: int = 0
        self.user_answers: List[Optional[str]] = []
        self.is_active: bool = False
        self.is_finished: bool = False
        self.last_result: Optional[QuizResult] = None

    def start_quiz(self, questions: List[Dict[str, Any]]) -> None:
        self.reset()
        self.questions = questions
        self.user_answers = [None] * len(questions)
        self.is_active = True

    @property
    def total_questions(self) -> int:
        return len(self.questions)

    def current_question(self) -> Optional[Dict[str, Any]]:
        if not self.is_active or self.current_index >= self.total_questions:
            return None
        return self.questions[self.current_index]

    def submit_answer(self, option_letter: Optional[str]) -> None:
        if not self.is_active or self.current_index >= self.total_questions:
            return
        self.user_answers[self.current_index] = option_letter
        self.current_index += 1
        if self.current_index >= self.total_questions:
            self.is_finished = True

    def progress_percentage(self) -> int:
        if self.total_questions == 0:
            return 0
        answered = sum(1 for a in self.user_answers if a is not None)
        return int((answered / self.total_questions) * 100)

    def finish_quiz(self) -> QuizResult:
        self.is_active = False
        correct = 0
        details: List[Dict[str, Any]] = []

        for idx, q in enumerate(self.questions):
            correct_answer = q.get("answer")
            user_answer = self.user_answers[idx]
            is_correct = user_answer == correct_answer
            if is_correct:
                correct += 1

            details.append(
                {
                    "question": q.get("question"),
                    "options": q.get("options"),
                    "correct_answer": correct_answer,
                    "user_answer": user_answer,
                    "explanation": q.get("explanation"),
                    "is_correct": is_correct,
                }
            )

        total = self.total_questions or 1
        percentage = (correct / total) * 100.0
        result = QuizResult(score=correct, total=total, percentage=percentage, details=details)
        self.last_result = result
        return result


"""
UserStory + AcceptanceCriteria をまとめたオブジェクト
システム内ではこのオブジェクトを「チケット」のように扱う
"""

from pydantic import BaseModel
from .user_story import UserStory
from .acceptance_criteria import AcceptanceCriteria


class UserStoryAcceptanceCriteria(BaseModel):
    user_story: UserStory
    acceptance_criteria: AcceptanceCriteria


if __name__ == "__main__":
    sample = UserStoryAcceptanceCriteria(
        user_story=UserStory(
            domain="IAM",
            persona="Corporate Employee",
            action="authenticate using credentials",
            reason="access internal systems securely"
        ),
        acceptance_criteria=AcceptanceCriteria(
            acceptance_criteria=[
                "JWT is issued on success",
                "Invalid credentials return 401"
            ]
        )
    )
    print(sample.model_dump())

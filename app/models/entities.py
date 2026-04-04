from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class TicketStatus(StrEnum):
    OPEN = "open"
    ANSWERED = "answered"
    REJECTED = "rejected"


class AttemptStatus(StrEnum):
    STARTED = "started"
    COMPLETED = "completed"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telegram_first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telegram_last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    referral_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    language: Mapped[str] = mapped_column(String(32), default="uz_latin")
    is_profile_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    referral_score: Mapped[int] = mapped_column(Integer, default=0)
    invited_users_count: Mapped[int] = mapped_column(Integer, default=0)
    referrer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    referral_reward_granted: Mapped[bool] = mapped_column(Boolean, default=False)

    referrer: Mapped["User | None"] = relationship(remote_side=[id], backref="referrals")
    profile: Mapped["UserProfile | None"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    attempts: Mapped[list["TestAttempt"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    tickets: Mapped[list["SupportTicket"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class UserProfile(TimestampMixin, Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(255))
    last_name: Mapped[str] = mapped_column(String(255))
    patronymic: Mapped[str] = mapped_column(String(255))
    region: Mapped[str] = mapped_column(String(255))
    district: Mapped[str] = mapped_column(String(255))
    school_class: Mapped[int] = mapped_column(Integer)

    user: Mapped["User"] = relationship(back_populates="profile")


class RequiredChannel(TimestampMixin, Base):
    __tablename__ = "required_channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    chat_id: Mapped[int] = mapped_column(unique=True)
    invite_link: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ContestRule(TimestampMixin, Base):
    __tablename__ = "contest_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    media_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ContestBook(TimestampMixin, Base):
    __tablename__ = "contest_books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    media_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Test(TimestampMixin, Base):
    __tablename__ = "tests"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    test_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    answer_key: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_telegram_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_referrals: Mapped[int] = mapped_column(Integer, default=3)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    scheduled_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    questions: Mapped[list["Question"]] = relationship(back_populates="test", cascade="all, delete-orphan", order_by="Question.order_index")
    attempts: Mapped[list["TestAttempt"]] = relationship(back_populates="test", cascade="all, delete-orphan")


class Question(TimestampMixin, Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    image_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    test: Mapped["Test"] = relationship(back_populates="questions")
    options: Mapped[list["QuestionOption"]] = relationship(back_populates="question", cascade="all, delete-orphan")


class QuestionOption(TimestampMixin, Base):
    __tablename__ = "question_options"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)

    question: Mapped["Question"] = relationship(back_populates="options")


class TestAttempt(TimestampMixin, Base):
    __tablename__ = "test_attempts"
    __table_args__ = (UniqueConstraint("user_id", "test_id", name="uq_user_test_attempt"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"), index=True)
    score: Mapped[int] = mapped_column(Integer, default=0)
    total_questions: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default=AttemptStatus.STARTED.value)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="attempts")
    test: Mapped["Test"] = relationship(back_populates="attempts")
    answers: Mapped[list["TestAnswer"]] = relationship(back_populates="attempt", cascade="all, delete-orphan")


class TestAnswer(TimestampMixin, Base):
    __tablename__ = "test_answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("test_attempts.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    option_id: Mapped[int] = mapped_column(ForeignKey("question_options.id"))
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)

    attempt: Mapped["TestAttempt"] = relationship(back_populates="answers")
    question: Mapped["Question"] = relationship()
    option: Mapped["QuestionOption"] = relationship()


class SupportTicket(TimestampMixin, Base):
    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_file_id: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    media_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=TicketStatus.OPEN.value)
    admin_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="tickets")


class ScheduledBroadcast(TimestampMixin, Base):
    __tablename__ = "scheduled_broadcasts"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_text: Mapped[str] = mapped_column(Text)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BotConfig(TimestampMixin, Base):
    __tablename__ = "bot_config"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    referral_share_text: Mapped[str | None] = mapped_column(Text, nullable=True)

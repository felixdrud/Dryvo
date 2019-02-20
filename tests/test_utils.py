import json
from datetime import datetime, timedelta

import flask
import pytest

from server.api.database.mixins import Model
from server.api.database.models import Lesson
from server.api.utils import get_slots, jsonify_response
from server.consts import DATE_FORMAT, WORKDAY_DATE_FORMAT


def test_jsonify_response(app):
    msg = {'message': 'testing'}

    @jsonify_response
    def func():
        return msg
    with app.app_context():
        resp, code = func()
        assert code == 200
        assert json.loads(resp.response[0]) == msg


def test_get_slots():
    from_hour = datetime.now()
    to_hour = from_hour + timedelta(hours=1)
    duration = timedelta(minutes=30)
    taken = [(from_hour, from_hour + duration)]
    slots = get_slots((from_hour, to_hour), taken, duration)
    assert slots == [(from_hour + timedelta(minutes=30), to_hour)]


def test_sort_data(teacher, student, meetup, dropoff):
    lessons = []
    for _ in range(3):
        lessons.append(Lesson.create(teacher=teacher, student=student, creator=student.user,
                                     duration=40, date=datetime.now(),
                                     meetup_place=meetup, dropoff_place=dropoff))
    args = {"order_by": "created_at desc"}
    lessons_from_db = Lesson.query.order_by(Lesson._sort_data(
        args, default_column="created_at")).all()
    assert lessons_from_db[0] == lessons[-1]
    args = {"order_by": ""}
    lessons_from_db = Lesson.query.order_by(Lesson._sort_data(
        args, default_column="created_at", default_method="asc")).all()
    assert lessons_from_db[-1] == lessons[-1]


def test_filter_data(teacher, student, meetup, dropoff):
    date = datetime.now() + timedelta(days=100)
    lesson = Lesson.create(teacher=teacher, student=student, creator=student.user,
                           duration=40, date=date,
                           meetup_place=meetup, dropoff_place=dropoff)
    # date=ge:DATE
    date = datetime.strftime(date, DATE_FORMAT)
    lessons_from_db = Lesson.query.filter(Lesson._filter_data(
        "date", f"ge:{date}")).all()
    assert lessons_from_db[0] == lesson
    # student_id=2
    lessons_from_db = Lesson.query.filter(Lesson._filter_data(
        "student_id", 2)).all()
    assert not lessons_from_db
    # date=gggg:DATE
    lessons_from_db = Lesson.query.filter(Lesson._filter_data(
        "date", f"ggfggg:{date}")).all()  # supposed to translate to equal
    assert lessons_from_db[0] == lesson
    # date=DATE
    with pytest.raises(ValueError):
        lessons_from_db = Lesson.query.filter(Lesson._filter_data(
            "date", f"{date}")).all()


def test_filter_and_sort(teacher, student, meetup, dropoff):
    """test that limit is maxed to 100, base query, custom date, non allowed filters"""
    date = datetime.now() + timedelta(days=100)
    for x in range(101):
        Lesson.create(teacher_id=x, student=student, creator=student.user,
                      duration=40, date=date,
                      meetup_place=meetup, dropoff_place=dropoff)

    args = {"teacher_id": teacher.id}  # not allowed
    default_column = "date"
    query = None
    lessons_from_db = Lesson.filter_and_sort(args,
                                             default_sort_column=default_column,
                                             query=query)
    assert len(lessons_from_db) == 102
    args = {"date": date.strftime(WORKDAY_DATE_FORMAT)}
    lessons_from_db = Lesson.filter_and_sort(args,
                                             default_sort_column=default_column,
                                             query=query,
                                             custom_date=lambda x: datetime.strptime(x, WORKDAY_DATE_FORMAT))
    assert not lessons_from_db
    query = Lesson.query.filter_by(teacher_id=3)
    args = {}
    lessons_from_db = Lesson.filter_and_sort(args,
                                             default_sort_column=default_column,
                                             query=query)
    assert len(lessons_from_db) == 1
    query = None
    args = {"limit": 100000000000000}
    lessons_from_db = Lesson.filter_and_sort(args,
                                             default_sort_column=default_column,
                                             query=query,
                                             with_pagination=True)
    assert len(lessons_from_db.items) == 100

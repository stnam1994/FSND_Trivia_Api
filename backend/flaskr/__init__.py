import os
from flask import Flask, request, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import random
import re

from models import setup_db, Question, Category

QUESTIONS_PER_PAGE = 10


def create_app(test_config=None):
    app = Flask(__name__)
    setup_db(app)

    # Allow Cross-Origin Resource Sharing from /api endpoint
    cors = CORS(app, resources={r"/api/*": {"origins": "*"}})

    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Headers',
                             'Content-Type,Authorization,true')
        response.headers.add('Access-Control-Allow-Methods',
                             'GET,PATCH,POST,DELETE,OPTIONS')
        return response

    # GET route to retrieve all trivia categories.
    @app.route("/categories")
    def get_categories():
        try:
            categories = list(map(Category.format, Category.query.all()))
            result = {
                "success": True,
                "categories": categories
            }, 200
        except Exception:
            abort(500)

    # GET route to retrieve questions.
    # Questions are paginated to load only 10 at a time.
    @app.route('/questions')
    def get_questions():
        questions = Question.query.order_by(Question.id).all()
        total_questions = len(questions)
        categories = Category.query.order_by(Category.id).all()

        # Get paginated questions (10 per page)
        current_questions = get_paginated_questions(request, questions, 10)

        if (len(current_questions) == 0):
            abort(404)

        categories_dict = {}
        for category in categories:
            categories_dict[category.id] = category.type

        return jsonify({
            'success': True,
            'total_questions': total_questions,
            'categories': categories_dict,
            'questions': current_questions
        }), 200

    # DELETE a question by its id
    @app.route('/questions/<int:q_id>', methods=['DELETE'])
    def delete_question(q_id):
        question = Question.query.get(q_id)

        if not question:
            return abort(404, f'Question with ID: {q_id} is invalid.')

        question.delete()

        return jsonify({
            'deleted': q_id
        })

    # POST a new question
    @app.route('/questions', methods=['POST'])
    def post_question():
        question = request.json.get('question')
        answer = request.json.get('answer')
        category = request.json.get('category')
        difficulty = request.json.get('difficulty')

        if not (question and answer and category and difficulty):
            return abort(400, 'Request is missing one or more required keys.')

        question_entry = Question(question, answer, category, difficulty)
        question_entry.insert()

        return jsonify({
            'question': question_entry.format()
        })

    # Search questions by a search term
    @app.route('/search', methods=['POST'])
    def search():
        search_term = request.json.get('searchTerm', '')
        questions = [question.format() for question in Question.query.all() if
                     re.search(search_term, question.question, re.IGNORECASE)]

        return jsonify({
            'questions': questions,
            'total_questions': len(questions)
        })

    # GET questions based on category id
    @app.route('/categories/<int:cat_id>/questions', methods=['GET'])
    def get_questions_by_category(cat_id):
        if not cat_id:
            return abort(400, f'Category with ID: {cat_id} is invalid.')

        questions = [question.format() for question in
                     Question.query.filter(Question.category == cat_id)]

        return jsonify({
            'questions': questions,
            'total_questions': len(questions),
            'current_category': cat_id
        })

    # GET questions for a single quiz game
    @app.route('/quizzes', methods=['POST'])
    def get_quiz_questions():
        previous_questions = request.json.get('previous_questions')
        quiz_category = request.json.get('quiz_category')

        if not quiz_category:
            return abort(400, 'Required keys missing from request body')

        category_id = int(quiz_category.get('id'))
        questions = Question.query.filter(
            Question.category == category_id,
            ~Question.id.in_(previous_questions)) if category_id else \
            Question.query.filter(~Question.id.in_(previous_questions))

        question = questions.order_by(func.random()).first()

        if not question:
            return jsonify({})

        return jsonify({
            'question': question.format()
        })

    # Error handlers for 4xx
    @app.errorhandler(HTTPException)
    def http_exception_handler(error):
        return jsonify({
            'success': False,
            'error': error.code,
            'message': error.description
        }), error.code

    # Error handler for 500
    @app.errorhandler(Exception)
    def exception_handler(error):
        return jsonify({
            'success': False,
            'error': 500,
            'message': f'Oops! Something went wrong on our end: {error}'
        }), 500

    # Helper method for paginating questions
    # Only returns questions for the requested page number
    def get_paginated_questions(request, questions, num_of_questions):
        page = request.args.get('page', 1, type=int)
        questions = [question.format() for question in questions]

        start = (page - 1) * num_of_questions
        end = start + num_of_questions
        current_questions = questions[start:end]

        return current_questions

    return app

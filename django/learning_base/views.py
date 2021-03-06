"""
This module contains all directly accessed API functions
Views are not documented extensively in the code but at
https://github.com/Iliricon/clonecademy
"""
from django.http import HttpResponse
from django.core.mail import send_mail
from django.contrib.auth.models import User, Group
from django.utils import timezone
from django.utils.crypto import get_random_string

from rest_framework import status
from rest_framework import authentication, permissions
from rest_framework.views import APIView
from rest_framework.exceptions import ParseError, PermissionDenied
from rest_framework.response import Response

from . import custom_permissions
from . import serializers
from .models import Course, CourseCategory, Try, Profile, started_courses, QuizQuestion


class CategoryView(APIView):
    """
    Shows, creates, updates and deletes a category
    :author: Claas Voelcker, Tobias Huber
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (custom_permissions.IsAdminOrReadOnly,)

    def get(self, request, format=None):
        """
        Shows the categories
        :author: Claas Voelcker
        :return: a list of all categories
        """
        categories = CourseCategory.objects.all()
        data = serializers.CourseCategorySerializer(categories, many=True).data
        return Response(data,
                        status=status.HTTP_200_OK)

    def post(self, request, format=None):
        """
        everything else but displaying
        :author: Tobias Huber
        """
        data = request.data
        # check if instance shall be deleted
        if 'delete' in data:

            # if 'delete' is false return the names of coures which will be deleted
            if data['delete'] == False:
                category = CourseCategory.objects.filter(id=data['id'])
                if not category.exists():
                    return Response({'error': 'this category does not exist'},
                        status=status.HTTP_400_BAD_REQUEST)
                category = category.first()
                response = {}
                response['name'] = category.name
                response['courses'] = []
                for course in category.course_set.all():
                    response['courses'].append(course.name)
                return Response(response, status=status.HTTP_200_OK)

            # if 'delete' is true delete this category
            if data['delete'] == True:
                if 'id' in data:
                    instance = CourseCategory.objects.filter(id=data['id'])
                    if not instance.exists():
                        return Response({'error': 'a category with the given id'
                                                + ' does not exist'},
                                                status=status.HTTP_404_NOT_FOUND)
                    instance.first().delete()
                    return Response({'id': data['id']}, status=status.HTTP_200_OK)


        # check if an id is given, signaling to update the corresponding cat.
        if 'id' in data:
            category_id = data['id']
            if CourseCategory.objects.filter(id=category_id).exists():
                category = CourseCategory.objects.get(id=category_id)
                serializer = serializers.CourseCategorySerializer(
                    category, data=data )

            else:
                return Response(
                    {'error': 'a category with the id ' + str(category_id)
                            + ' does not exist'},
                    status=status.HTTP_404_NOT_FOUND)
        else:
            # else just create a plain serializer
            serializer = serializers.CourseCategorySerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data,
                            status=status.HTTP_200_OK)
        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)


class MultiCourseView(APIView):
    """
    View to see all courses of a language. The post method provides a general
    interface with three filter settings.
    @author Claas Voelcker
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, format=None):
        """
        Not implemented
        """
        return Response({'error': 'Method not allowed'},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def post(self, request, format=None):
        """
        Returns a set of courses detailed by the query. It expects a request
        with the keys 'language', 'category', 'type'. The returning JSON
        corresponds to the values. All values can be empty strings, resulting
        in all courses being returned.
        """
        try:
            types = ['mod', 'started']
            categories = [str(x) for x in CourseCategory.objects.all()]
            languages = [x[0] for x in Course.LANGUAGES]
            data = request.data
            r_type = data['type']
            r_category = data['category']
            r_lan = data['language']

            # checks whether the query only contains acceptable keys
            if not ((r_type in types or not r_type)
                    and (r_category in categories or not r_category)
                    and (r_lan in languages or not r_lan)):
                return Response({'error': 'Query not possible'},
                                status=status.HTTP_400_BAD_REQUEST)

            courses = Course.objects.all()
            courses = courses.filter(language=r_lan)

            # filter invisible courses if neccessary
            if not (request.user.profile.is_mod()
                    or request.user.profile.is_admin()):
                courses = courses.filter(is_visible=True)

            if r_category != '':
                category = CourseCategory.objects.filter(
                    name=r_category).first()
                courses = courses.filter(category=category)
            if r_type == 'mod':
                courses = courses.filter(responsible_mod=request.user)
            elif r_type == 'started':
                courses = started_courses(request.user)
            data = serializers.CourseSerializer(courses, many=True, context={
                'request': request}).data
            return Response(data, status=status.HTTP_200_OK)
        except Exception as errors:
            return Response({'error': 'Query not possible' + str(errors)},
                            status=status.HTTP_400_BAD_REQUEST)


class CourseEditView(APIView):
    """
    contains all the code related to edit a courses
    TODO: this is probably redundant code
    @author Leonhard Wiedmann
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (custom_permissions.IsModOrAdmin,)

    def get(self, request, course_id=None, format=None):
        """
        Returns all the information about a course with the answers and the
        solutions
        """
        if not course_id:
            return Response({'error': 'Method not allowed'},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)

        try:
            course = Course.objects.filter(id=course_id).first()
            course_serializer = serializers.CourseEditSerializer(
                course,
                context={
                    'request': request})
            data = course_serializer.data
            return Response(data)

        except Exception as errors:
            return Response({'error': str(errors)},
                            status=status.HTTP_404_NOT_FOUND)

    def post(self, request, course_id=None, format=None):
        """
        Not implemented
        """
        data = request.data
        if data['delete']:
            groups = request.user.groups.values_list('name', flat=True)

            if 'admin' in groups:
                course = Course.objects.filter(id=course_id)
                if not course.exists():
                    return Response({'error': 'Course does not exist'},
                        status=status.HTTP_404_NOT_FOUND)
                course.first().delete()
                return Response({'deleted': course_id}, status=status.HTTP_200_OK)
        return Response({'error': 'Method not allowed'},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)


class CourseView(APIView):
    """
    Contains all code related to viewing and saving courses.
    :author: Claas Voelcker
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (
        custom_permissions.IsModOrAdminOrReadOnly,)

    def get(self, request, course_id=None, format=None):
        """
        Returns a course if the course_id exists. The course, it's
        modules and questions are serialized.

        :author: Claas Voelcker
        :param request: request object containing auth token and user id
        :param course_id: the id of the required course
        :param format: unused (inherited)
        :return: a response containing the course serialization
        """

        # if no course id is given, the method was called wrong
        if not course_id:
            return Response({'error': 'Method not allowed'},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)
        try:
            # fetch the course object, serialize it and return
            # the serialization
            course = Course.objects.filter(id=course_id).first()
            data = serializers.CourseSerializer(course, context={
                'request': request}).data
            data['quiz'] = False
            if len(course.quizquestion_set.all()) > 0:
                data['quiz'] = True
            return Response(data,
                            status=status.HTTP_200_OK)
        # in case of an exception, throw a "Course not found" error for the
        # frontend, packaged in a valid response with an error status code
        except Exception as e:
            return Response({'error': str(e)},
                            status=status.HTTP_404_NOT_FOUND)

    def post(self, request, course_id=None, format=None):
        """
        Saves a course to the database. If the course id is provided,
        the method updates and existing course, otherwise, a new course
        is created.

        :author: Tobias Huber, Claas Voelcker
        :param request: request containig the user and auth token
        :param course_id: optional: the course id
                    (if a course is edited instead of created)
        :param format: unused (inherited)
        :return: a status response giving feedback about errors or a sucessful
                    database access to the frontend
        """

        data = request.data

        # checks whether the request contains any data
        if data is None:
            return Response({'error': 'Request does not contain data'},
                            status=status.HTTP_400_BAD_REQUEST)

        course_id = data.get('id')
        # Checks whether the name of the new course is unique
        if (course_id is None) and Course.objects.filter(
                name=data['name']).exists():
            return Response({'error': 'Course with that name exists'},
                            status=status.HTTP_409_CONFLICT)

        # adds the user of the request to the data
        if course_id is None:
            data['responsible_mod'] = request.user
        # if the course is edited, check for editing permission
        else:
            responsible_mod = Course.objects.get(id=course_id).responsible_mod
            # decline access if user is neither admin nor the responsible mod
            if (request.user.profile.is_admin()
                    or request.user == responsible_mod):
                data['responsible_mod'] = responsible_mod
            else:
                raise PermissionDenied(detail="You're not allowed to edit this"
                                       + "course, since you're not the"
                                       + 'responsible mod',
                                       code=None)

        # serialize the course
        course_serializer = serializers.CourseSerializer(data=data)

        # check for serialization errors
        if not course_serializer.is_valid():
            return Response({'error': course_serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)

        # send the data to the frontend
        else:
            try:
                course_serializer.create(data)
                return Response({'success': 'Course saved'},
                                status=status.HTTP_201_CREATED)
            except ParseError as error:
                return Response({'error': str(error)},
                                status=status.HTTP_400_BAD_REQUEST)


class ToggleCourseVisibilityView(APIView):
    """
    changes the visibility of a course

    alternatively sets the visibility to the provided state
    {
        "is_visible": (optional) True|False
    }

    @author Tobias Huber
    """

    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (custom_permissions.IsAdmin,)

    def post(self, request, course_id):
        """
        Sets the course visibility to the given value
        :param request: request object from the rest dispatcher
        :param course_id: the id of the course whos visibility shall be changed
        :return: a REST Response with a meaningfull JSON formatted message
        """
        if course_id is None:
            return Response({'error': 'course_id must be provided'},
                            status=status.HTTP_400_BAD_REQUEST)
        elif not Course.objects.filter(id=course_id).exists():
            return Response({'error': 'course not found. id: ' + course_id},
                            status=status.HTTP_404_NOT_FOUND)
        else:
            course = Course.objects.get(id=course_id)
            if 'is_visible' in request.data:
                if not (request.data['is_visible'] == 'true'
                        or request.data['is_visible'] == 'false'):
                    Response({'ans':'is_visible must be "true" or "false" of type string'})
                course.is_visible = request.data['is_visible'] == 'true'
            else:
                course.is_visible = not course.is_visible
            course.save()
            return Response({'is_visible': course.is_visible},
                            status=status.HTTP_200_OK)


class ModuleView(APIView):
    """
    Shows a module
    @author Claas Voelcker
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, course_id, module_id, format=None):
        """
        Not implemented
        """
        return Response({'error': 'Method not allowed'},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def post(self, request, format=None):
        """
        Not implemented
        """
        return Response({'error': 'Method not allowed'},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)


class QuestionView(APIView):
    """
    View to show questions and to evaluate them. This does not return the
    answers, which are given by a separate class.
    @author Claas Voelcker
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def can_access_question(user, question, module_id, question_id):
        """
        Checks if the question is accessable by the user (all questions before
        need to be answered correctly)
        :param user: user wanting to access
        :param question: question to be accessed
        :param module_id: module id the question belongs to
        :param question_id: the questions id
        :return: True|False (see description)
        @author Tobias Huber
        """
        module = question.module
        first_question = int(module_id) <= 0 and int(question_id) <= 0
        if first_question:
            return True
        elif (not first_question
              and question.get_previous_in_order()
              and Try.objects.filter(
                  user=user,
                  question=question.get_previous_in_order(),
                  solved=True)):
            return True
        elif (not module.is_first_module()
              and module.get_previous_in_order()
              and Try.objects.filter(
                  user=user,
                  question=module.get_previous_in_order().question_set.all()[0],
                  solved=True)):
            return True
        return False

    def get(self, request, course_id, module_id, question_id, format=None):
        """
        Get a question together with additional information about the module
        and position (last_module and last_question keys)
        """
        try:
            course = Course.objects.get(id=course_id)
            course_module = course.module_set.all()[int(module_id)]
            question = course_module.question_set.all()[int(question_id)]

            if question is None:
                return Response({'error': 'Question not found'},
                                status=status.HTTP_404_NOT_FOUND)
            if not self.can_access_question(request.user, question, module_id,
                                            question_id):
                return Response({'error': "Previous question(s) haven't been "
                                        'answered correctly yet'},
                                status=status.HTTP_403_FORBIDDEN)
            data = serializers.QuestionSerializer(question,
                                                  context={'request': request})
            data = data.data
            return Response(data, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({'error': str(error)},
                            status=status.HTTP_404_NOT_FOUND)

    def post(self, request, course_id, module_id, question_id, format=None):
        """
        Evaluates the answer to a question.
        @author Tobias Huber
        """
        try:
            course = Course.objects.get(id=course_id)
            course_module = course.module_set.all()[int(module_id)]
            question = course_module.question_set.all()[int(question_id)]
        except Exception:
            return Response({'error': 'Question not found'},
                            status=status.HTTP_404_NOT_FOUND)
        # deny access if there is a/are previous question(s) and it/they
        # haven't been answered correctly
        if not (self.can_access_question(request.user, question, module_id,
                                         question_id)):
            return Response(
                {'error': "Previous question(s) haven't been answered"
                        + " correctly yet"},
                status=status.HTTP_403_FORBIDDEN
            )

        solved = question.evaluate(request.data["answers"])

        # only saves the points if the question hasn't been answered yet
        if solved and not question.try_set.filter(
                user=request.user, solved=True).exists():
            request.user.profile.ranking += question.get_points()
            request.user.profile.save()
        Try(user=request.user, question=question,
            answer=str(request.data["answers"]), solved=solved).save()
        response = {"evaluate": solved}
        if solved:
            next_type = ""
            if not question.is_last_question():
                next_type = str(course_id) + '/' + str(int(module_id) + 1) + '/' + str(int(question_id) + 2)
            elif not course_module.is_last_module():
                next_type = str(course_id) + '/' + str(int(module_id) + 2) + '/1'
            elif course.quizquestion_set.exists():
                response['quiz'] = True
            response['course'] = course_id
            response['next'] = next_type

            if question.feedback:
                # response['custom_feedback'] = question.custom_feedback()
                response['feedback'] = question.feedback
        return Response(response)


class AnswerView(APIView):
    """
    Shows all possible answers to a question.
    :author: Claas Voelcker
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, course_id, module_id, question_id, format=None):
        """
        Lists the answers for a question
        """
        course = Course.objects.get(id=course_id)
        module = course.module_set.all()[int(module_id)]
        question = module.question_set.all()[int(question_id)]
        answers = question.answer_set()
        data = [serializers.get_answer_serializer(answer) for answer in
                answers]
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request, format=None):
        """
        Not implemented
        :param request:
        :param format:
        :return:
        """
        return Response({"error": 'Method not allowed'},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)


def calculate_quiz_points(old_percentage, new_percentage, difficulty):
    """
    calculates the quiz points from the old existing statistics and the new
    quiz answers
    :param old_percentage: percentage of questions already answered correctly
    :param new_percentage: percentage of questions newly answered correctly
    :param difficulty: the course difficulty
    :return: the additional points
    """
    multiplier = 2 if difficulty == 2 else 1
    ranking_threshold = [0.4, 0.7, 0.9]
    old_extra_points = [x[0] for x in enumerate(ranking_threshold) if
                        x[1] > old_percentage]
    new_extra_points = [x[0] for x in enumerate(ranking_threshold) if
                        x[1] > new_percentage]
    old_extra_points = 3 if not old_extra_points else old_extra_points[0]
    new_extra_points = 3 if not new_extra_points else new_extra_points[0]
    return max(0, 5 * multiplier * (new_extra_points - old_extra_points))


class QuizView(APIView):
    """
    Shows the quiz question of the current course in get
    evaluates this quiz question in post
    @author Leonhard Wiedmann
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, course_id):
        """
        Shows the current quiz question if it exists.
        When this id does not exist throws error message
        """
        course = Course.objects.filter(id=course_id).first()

        # check if user did last question of the last module
        # if valid the course is completed
        module = course.module_set.all()[len(course.module_set.all()) - 1]
        question = module.question_set.all(
        )[len(module.question_set.all()) - 1]
        if not Try.objects.filter(question=question, solved=True).exists():
            return Response({"error": "complete the course first"},
                            status=status.HTTP_403_FORBIDDEN)

        quiz = course.quizquestion_set.all()
        if len(quiz) in range(5, 21):
            quiz = serializers.QuizSerializer(quiz, many=True)

            return Response(quiz.data)
        return Response({"error": "this quiz is invalid"},
                        status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, course_id, format=None):
        """
        Resolves this quiz question for the current user.
        """
        # post does two things (return feedback for questions and whole quiz)
        # this switch/case differentiates between the two
        if request.data['type'] == "check_answers":
            course = Course.objects.get(id=course_id)
            quiz = course.quizquestion_set.all()
            all_question_length = len(quiz)
            if all_question_length <= 0:
                return Response({"error": "this quiz does not exist"},
                                status=status.HTTP_404_NOT_FOUND)
            # checks if the submission is wrong (different lengths of the
            # arrays)
            if len(quiz) != len(request.data['answers']):
                resp = "the quiz has {} question and your evaluation has {}"\
                    .format(len(quiz), len(request.data['answers']))
                return Response({"error": resp, "test": request.data},
                                status=status.HTTP_400_BAD_REQUEST)
            response = []
            newly_solved = 0
            old_solved = 0
            for i, quiz_entry in enumerate(quiz):
                answer_solved = request.data['answers'][i]
                for answer in request.data['answers']:
                    if 'id' in answer and quiz_entry.id is answer['id']:
                        answer.pop('id')
                        answer_solved = answer
                        break
                solved = quiz_entry.evaluate(answer_solved)
                points = 0
                if solved and not quiz_entry.try_set.filter(
                        user=request.user, solved=True).exists():
                    points = 1
                    newly_solved += 1
                    request.user.profile.ranking += quiz_entry.get_points()
                elif quiz_entry.try_set.filter(user=request.user,
                                               solved=True).exists():
                    old_solved += 1
                Try(user=request.user, quiz_question=quiz_entry,
                    answer=str(request.data), solved=solved).save()

                response.append({"name": quiz[i].question, "solved": solved, 'points': points})

            old_extra = float(old_solved / all_question_length)
            new_extra = float(
                (newly_solved + old_solved) / all_question_length)
            request.user.profile.ranking += calculate_quiz_points(
                old_extra, new_extra, course.difficulty)
            request.user.profile.save()

            return Response(response, status=status.HTTP_200_OK)
        if request.data['type'] == 'get_answers':
            course = Course.objects.get(id=course_id)
            quiz_question = QuizQuestion.objects.filter(id=request.data['id']).first()
            answers = [answer.id for answer in
                       quiz_question.quizanswer_set.all() if answer.correct]
            return Response({'answers': answers}, status.HTTP_200_OK)
        return Response({'error': 'Could not process request'},
                        status.HTTP_400_BAD_REQUEST)


class UserView(APIView):
    """
    Shows a user profile
    @author Claas Voelcker
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, user_id=False, format=None):
        """
        Shows the profile of any user if the requester is mod,
        or the profile of the requester

        TODO: If the behaviour that an admin is allowed to receive information
        about a specific user, will be used again,
        a custom_permission should be written.
        """
        user = request.user
        if user_id:
            if user.profile.is_admin():
                user = User.objects.filter(id=user_id).first()
                if not user:
                    return Response({'error': 'User not found'},
                                    status=status.HTTP_404_NOT_FOUND)
            else:
                raise PermissionDenied(detail=None, code=None)

        user = serializers.UserSerializer(user)
        return Response(user.data)

    def post(self, request, format=None):
        """
        Post is used to update the profile of the requesting user
        @author Tobias Huber
        """
        user = request.user
        data = request.data

        if 'oldpassword' in data:
            if not request.user.check_password(request.data['oldpassword']):
                return Response({'error': 'given password is incorrect'},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'error': 'password is required'},
                            status=status.HTTP_400_BAD_REQUEST)

        user_serializer = serializers.UserSerializer(user, data=data,
                                                     partial=True)
        if user_serializer.is_valid():
            user_serializer = user_serializer.update(
                user,
                validated_data=request.data)
            return Response({'ans': 'Updated user ' + user.username},
                            status=status.HTTP_200_OK)
        return Response(user_serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)


class UserRegisterView(APIView):
    """
    Saves a new user
    @author Tobias Huber
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request, user_id=False, format=None):
        """
        Saves a new user.
        """
        if user_id:
            return Response({'error': 'Please use the UserView to update data'},
                            status=status.HTTP_403_FORBIDDEN)
        user_serializer = serializers.UserSerializer(data=request.data)
        if user_serializer.is_valid():
            user_serializer.create(request.data)
            return Response({'ans': 'Created a new user'},
                            status=status.HTTP_201_CREATED)
        return Response(user_serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)


class MultiUserView(APIView):
    """
    Shows an overview over all users
    @author Claas Voelcker
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (custom_permissions.IsAdmin,)

    def get(self, request):
        """
        Returns all users
        """
        users = User.objects.all()
        data = serializers.UserSerializer(users, many=True).data
        return Response(data)

    def post(self, request, format=None):
        """
        Not implemented
        """
        return Response({'error': 'Method not allowed'},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)


class StatisticsView(APIView):
    """
    A class displaying statistics information for a given user. It is used to
    access the try object.
    @author: Claas Voelcker
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, user_id=None):
        """
        shows the statistics of the given user
        """
        user = request.user if not user_id else User.objects.get(id=user_id)
        tries = Try.objects.filter(user=user)
        data = serializers.TrySerializer(tries, many=True).data
        return Response(data)

    def post(self, request, format=None):
        """
        implements filtering logic for the statistics
        :param request:
        :param format:
        :return:
        """
        import time
        import csv
        data = request.data
        user = request.user

        tries = Try.objects.all()

        groups = user.groups.values_list('name', flat=True)

        is_mod = 'moderator' in groups or 'admin' in groups

        # the simplest call is if the user just wants its statistic
        print(data)
        print(data['id'])
        if 'id' in data and data['id'] == user.id:
            tries = tries.filter(user=user)

        # A moderator can get all statistics of his created courses
        # with 'get_courses' as in put the it will return all courses created
        # by this user
        elif is_mod and 'course' in data and 'admin' not in groups:
            tries = tries.filter(
                question__module__course__responsible_mod=user)

        # admins can get all statistics of all users
        elif 'admin' in groups:
            if 'id' in data:
                tries.filter(user__id=data['id'])
        else:
            return Response({'error': 'invalid userID'},
                            status=status.HTTP_403_FORBIDDEN)

        # return all statistics after prefiltering for this course
        if 'course' in data:

            tries = tries.filter(question__module__course__id=data['course'])

            if 'list_questions' in data:
                course = Course.objects.filter(id=data['course']).first()
                value = []
                index = 0
                for module in course.module_set.all():
                    value.append([])
                    for question in module.question_set.all():
                        value[index].append({'name': question.title,
                                             'solved': len(
                                                 question.try_set.filter(
                                                     solved=True).all()),
                                             'not solved': len(
                                                 question.try_set.filter(
                                                     solved=False).all())})
                    index += 1
                return Response(value)

        # get the statistics for a specific time
        if ('date' in data
                and 'start' in data['date']
                and 'end' in data['date']):
            start = data['date']['start']
            end = data['date']['end']
            tries = tries.filter(
                date__range=[start, end])

        # filter just for solved tries
        if 'solved' in data:
            tries = tries.filter(solved=data['solved'])

        # filter for a specific category
        if 'category' in data:
            tries = tries.filter(
                question__module__course__category__name=data['category'])

        # if this variable is set the view will return a array of dicts which
        # are {name: string, color: string, counter: number}
        if 'categories__with__counter' in data:
            categories = CourseCategory.objects.all()
            value = []
            for cat in categories:
                value.append(
                    {
                        'name': cat.name,
                        'color': cat.color,
                        'counter': len(tries.filter(
                            question__module__course__category=cat))
                    })
            return Response(value)

        serialize_data = None

        # filters the statistics and counts for the 'filter' variable
        if 'filter' in data:
            value = {}
            for trie in tries:
                if not str(getattr(trie, data['filter'])) in value:
                    value[str(getattr(trie, data['filter']))] = 1
                else:
                    value[str(getattr(trie, data['filter']))] += 1
            return Response(value)

        # this part orders the list for the 'order' value in the request
        if 'order' in data:
            tries = tries.order_by(data['order'])

        if 'serialize' in data:
            serialize_data = serializers.TrySerializer(tries, many=True,
                                                       context={
                                                           'serialize': data[
                                                               'serialize']}).data
        else:
            serialize_data = serializers.TrySerializer(tries, many=True).data

        if 'format' in data and data['format'] == 'csv':
            response = HttpResponse(content_type='text/csv')
            filename = time.strftime('%d/%m/%Y') + '-' + user.username + '.csv'
            content = 'attachment; filename="' + filename
            response['Content-Disposition'] = content
            writer = csv.writer(response)
            writer.writerow(['question', 'user', 'date', 'solved'])
            for row in serialize_data:
                profile = Profile.objects.get(user__username=row['user'])
                profile_hash = profile.get_hash()
                writer.writerow(
                    [row['question'],
                     profile_hash,
                     row['date'],
                     row['solved']])
            return response
        return Response(serialize_data)


class RankingView(APIView):
    """
    A view for the ranking. The get method returns an ordered list of all users
    according to their rank.
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, format=None):
        """
        API request for ranking information
        :param request: can be empty
        :param format: request: can be empty
        :return: a json response with ranking information
        """
        profiles = Profile.objects.all().reverse()
        data = serializers.RankingSerializer(profiles).data
        return Response(data)

    def post(self, request, format=None):
        """
        Not implemented
        """
        return Response({'error': 'Method not allowed'},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)


class RequestView(APIView):
    """
    The RequestView class is used to submit a request for moderator rights.

    The request can be accessed via "clonecademy/user/request/"
    @author Tobias Huber
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, format=None):
        """
        Returns True if request is allowed and False if request isn't allowed
        or the user is already mod.
        """
        allowed = (not request.user.profile.is_mod()
                   and request.user.profile.modrequest_allowed())
        return Response({'allowed': allowed},
                        status=status.HTTP_200_OK)

    def post(self, request, format=None):
        """
        Handels the moderator rights request. Expects a reason and extracts the
        user from the request header.
        """
        data = request.data
        user = request.user
        profile = user.profile
        if not user.profile.modrequest_allowed():
            return Response(
                {'error': 'User is mod or has sent too many requests'},
                status=status.HTTP_403_FORBIDDEN)
        # pay attention because there could be localization errors
        profile.last_modrequest = timezone.now()
        profile.save()
        send_mail(
            'Moderator rights requested by {}'.format(user.username),
            'The following user {} requested moderator rights for the'
            'CloneCademy platform. \n'
            'The given reason for this request: \n{}\n '
            'If you want to add this user to the moderator group, access the '
            'profile {} for the confirmation field.\n '
            'Have a nice day,\n your CloneCademy bot'.format(
                user.username, data['reason'],
                user.profile.get_link_to_profile()),
            'bot@clonecademy.de',
            [admin.email for
             admin in Group.objects.get(name='admin').user_set.all()]
        )
        return Response({'Request': 'ok'}, status=status.HTTP_200_OK)


class UserRightsView(APIView):
    """
    Used to promote or demote a given user (by id)

    This View is used to grant or revoke specific rights (user|moderator|admin)
    The POST data must include the following fields
    {"right": "moderator"|"admin",
    "action": "promote"|"demote"}.
    Returns the request.data if validation failed.

    The user_id is to be provided in the url.

    TODO: try the generic.create APIView. Its behaviour isn't really different
    from the current. It just provides additional success-headers in a way
    I do not understand.
    """

    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (custom_permissions.IsAdmin,)

    def post(self, request, user_id, format=None):
        """
        changes the group membership of the user
        """
        data = request.data
        right_choices = ['moderator', 'admin']
        action_choices = ['promote', 'demote']
        errors = {}

        # validation
        if not data['right'] or not data['right'] in right_choices:
            errors['right'] = ('this field is required and must be one of '
                               + 'the following options'
                               + ', '.join(right_choices))
        if not data['action'] or not data['action'] in action_choices:
            errors['action'] = ('this field is required and must be one of '
                                + 'the following options'
                                + ', '.join(action_choices))
        if not User.objects.filter(id=user_id).exists():
            errors['id'] = 'a user with the id #' + user_id + ' does not exist'
        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # actual behaviour
        user = User.objects.get(id=user_id)
        group = Group.objects.get(name=data['right'])
        action = data['action']
        if action == 'promote':
            user.groups.add(group)
        elif action == 'demote':
            user.groups.remove(group)
        return Response(serializers.UserSerializer(user).data)

    def get(self, request, user_id, format=None):
        """
        This API is for debug only.
        It comes in quite handy with the browsable API
        """
        user = User.objects.get(id=user_id)
        return Response({'username': user.username,
                         'is_mod?':
                             user.groups.filter(name='moderator').exists(),
                         'is_admin?':
                             user.groups.filter(name='admin').exists()})


class PwResetView(APIView):
    """
    Resets the password of a user and sends the new one to the email adress
    of the user

    {
        "email": the email of the user
    }
    """

    authentication_classes = ()
    permission_classes = ()

    def post(self, request, format=None):
        """
        Sends a mail to the user containing a new one time password
        :param request:
        :param format:
        :return:
        """
        data = request.data
        if 'email' not in data:
            return Response({'error': 'you must provide an email'},
                            status=status.HTTP_400_BAD_REQUEST)
        elif not User.objects.filter(email=data['email']).exists():
            return Response({'error': 'no user with email: ' + data['email']},
                            status=status.HTTP_404_NOT_FOUND)

        # if request data is valid:
        user = User.objects.get(email=data['email'])
        # generate a random password with the rand() implementation of
        # django.utils.crypto
        new_password = get_random_string(length=16)

        send_mail(
            'Password Reset on clonecademy.net',
            ('Hello {},\n \n'
             + 'You have requested a new password on clonecademy.net \n'
             + 'Your new password is: \n{} \n \n'
             + 'Please change it imediately! \n'
             + 'Have a nice day,\nyour CloneCademy bot').format(
                 user.username, new_password),
            'bot@clonecademy.de',
            [user.email]
        )
        user.set_password(new_password)
        user.save()
        return Response(status=status.HTTP_200_OK)

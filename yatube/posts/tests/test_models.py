from django.test import TestCase
from posts.models import Comment, Group, Post, User


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост, который предназначен для тестов.',
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text='Тестовый комментарий'
        )

    def test_models_have_correct_object_names(self):
        """.Проверяем, что у моделей корректно работает __str__."""
        expected_post_name = 'Тестовый пост, '
        expected_group_name = 'Тестовая группа'
        expected_comment_name = 'Тестовый коммен'
        with self.subTest(model='Post'):
            self.assertEqual(expected_post_name, str(PostModelTest.post))
        with self.subTest(model='Group'):
            self.assertEqual(expected_group_name, str(PostModelTest.group))
        with self.subTest(model='Comment'):
            self.assertEqual(expected_comment_name, str(PostModelTest.comment))

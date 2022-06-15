import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.forms import PostForm
from posts.models import Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsFormTests(TestCase):
    FIELDS_FOR_TESTS = (
        ('text', 'Текст поста', 'Текст нового поста'),
        ('group', 'Группа', 'Группа, к которой будет относиться пост'),
        ('image', 'Картинка', 'Загрузите картинку'),
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.form = PostForm()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание группы #'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text='Тестовый пост для формы'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PostsFormTests.user)
        self.post_id = PostsFormTests.post.id

    def test_post_creation(self):
        """.Проверяем корректность создания нового поста из формы."""
        initial_post_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый пост из формы',
            'group': PostsFormTests.group.pk,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response, reverse('posts:profile', args=('auth',)))
        self.assertEqual(Post.objects.count(), initial_post_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text='Тестовый пост из формы',
                author=PostsFormTests.user,
                group=PostsFormTests.group,
            ).exists(),
            msg='Текст или автор тестового поста не совпадает с ожидаемыми')

    def test_post_editing(self):
        """.Проверяем корректность обновления поста после редактирования."""
        initial_post_count = Post.objects.count()
        form_data = {
            'text': 'Обновлённый пост',
            'group': PostsFormTests.group.pk,
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', args=(self.post_id,)),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), initial_post_count)
        self.assertEqual(
            Post.objects.get(pk=self.post_id).text, 'Обновлённый пост')
        self.assertRedirects(
            response, reverse('posts:post_detail', args=(self.post_id,)))

    def test_post_form_labels(self):
        """.Проверяем правильность labels для полей формы PostForm."""
        for field, expected_label, _ in self.FIELDS_FOR_TESTS:
            form_label = PostsFormTests.form.fields[field].label
            with self.subTest(field_name=field):
                self.assertEqual(form_label, expected_label)

    def test_post_form_help_texts(self):
        """.Проверяем правильность help_texts для полей формы PostForm."""
        for field, _, expected_help_text in self.FIELDS_FOR_TESTS:
            form_help_text = PostsFormTests.form.fields[field].help_text
            with self.subTest(field_name=field):
                self.assertEqual(form_help_text, expected_help_text)

    def test_post_creation_with_an_image(self):
        """.Проверяем корректность создания нового поста с картинкой."""
        initial_post_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif',
        )
        form_data = {
            'text': 'Тестовый пост из формы',
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response, reverse('posts:profile', args=('auth',)))
        self.assertEqual(Post.objects.count(), initial_post_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text='Тестовый пост из формы',
                author=PostsFormTests.user,
                image='posts/small.gif'
            ).exists(),
            msg='Содержимое тестового поста не совпадает с ожидаемым')

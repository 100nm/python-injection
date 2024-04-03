from injection import inject

from ...sources.factories.user_factory import UserFactory


class TestUserFactory:
    @classmethod
    def setup_class(cls):
        cls.init_dependencies()

    @classmethod
    @inject
    def init_dependencies(cls, factory: UserFactory):
        cls.factory = factory

    def test_build_with_success_return_user(self):
        username = "test"
        password = "test"
        user = self.factory.build(
            {
                "username": username,
                "password": password,
            }
        )

        assert str(user.id) == "e3e70682-c209-4cac-a29f-6fbed82c07cd"
        assert user.username == username
        assert (
            user.password.get_secret_value()
            == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
        )

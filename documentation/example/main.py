from sources.factories.user_factory import UserFactory

from injection import inject


@inject
def main(user_factory: UserFactory):
    user = user_factory.build(
        {
            "username": "root",
            "password": "root",
        }
    )
    print("User:", user.model_dump_json(), sep=" ")


if __name__ == "__main__":
    main()

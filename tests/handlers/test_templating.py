import shutil
from pathlib import Path
from typing import Generator

import pytest
from starlette.testclient import TestClient

from cannula import CannulaApplication


@pytest.fixture
def template_dir(tmp_path) -> Generator[Path, None, None]:
    """
    Creates a temporary directory with the following structure:
    templates/
    ├── layout.html
    ├── app/
    │   ├── layout.html
    │   ├── page.html
    │   ├── users/
    │   │   ├── layout.html
    │   │   ├── page.html
    │   │   └── [id]/
    │   │       ├── layout.html
    │   │       └── page.html
    │   │   └── [id:uuid]/
    │   │       ├── layout.html
    │   │       └── page.html
    """
    # Create an operations file
    (tmp_path / "operations.graphql").write_text(
        """
        query Me { me { name } }
        query AllUsers($limit: Int) { all(limit: $limit) { name }}
    """
    )
    # Create an schema file
    (tmp_path / "schema.graphql").write_text(
        """
        type User {
            name: String
        }
        type Query {
            me: User
            you: User
            all(limit: Int = 10): [User]
        }
    """
    )
    # Create an pyproject.toml
    (tmp_path / "pyproject.toml").write_text(
        """
        [tool.cannula.codegen]
        app_directory = "templates"
    """
    )

    # Setup Templates
    templates = tmp_path / "templates"
    templates.mkdir()

    # Create an operation template
    operations_dir = templates / "_operations"
    operations_dir.mkdir()
    (operations_dir / "Me.html").write_text(
        """<p>Operation: {{ operation.name }}</p>"""
    )

    # Create root layout
    (templates / "layout.html").write_text(
        """
    <!DOCTYPE html>
    <html>
        <body>
            <header>Root Layout</header>
            {% block content %}{% endblock %}
        </body>
    </html>
    """
    )

    # Create root page
    (templates / "page.html").write_text(
        """
    {% extends "layout.html" %}
    {% block content %}ROOT{% endblock %}
    """
    )

    # Create hidden route should not be found
    hidden = templates / "_hidden"
    hidden.mkdir()
    (hidden / "page.html").write_text(
        """
    {% extends "layout.html" %}
    {% block content %}HIDDEN{% endblock %}
    """
    )

    # Create app directory structure
    app_dir = templates / "app"
    app_dir.mkdir()

    (app_dir / "layout.html").write_text(
        """
    {% extends "layout.html" %}
    {% block content %}
        <main>
            <nav>App Nav</nav>
            {% block app_content %}{% endblock %}
        </main>
    {% endblock %}
    """
    )

    (app_dir / "page.html").write_text(
        """
    {% extends "app/layout.html" %}
    {% block app_content %}
        <h1>App Home</h1>
    {% endblock %}
    """
    )

    # Create users section
    users_dir = app_dir / "users"
    users_dir.mkdir()

    (users_dir / "layout.html").write_text(
        """
    {% extends "app/layout.html" %}
    {% block app_content %}
        <div class="users-layout">
            {% block users_content %}{% endblock %}
        </div>
    {% endblock %}
    """
    )

    (users_dir / "page.html").write_text(
        """
    {% extends "app/users/layout.html" %}
    {% block users_content %}
        <h1>Users List</h1>
    {% endblock %}
    """
    )

    # Create user detail section
    user_detail_dir = users_dir / "[id]"
    user_detail_dir.mkdir()

    (user_detail_dir / "layout.html").write_text(
        """
    {% extends "app/users/layout.html" %}
    {% block users_content %}
        <div class="user-detail-layout">
            {% block user_detail_content %}{% endblock %}
        </div>
    {% endblock %}
    """
    )

    (user_detail_dir / "page.html").write_text(
        """
    {% extends "layout.html" %}
    {% block user_detail_content %}
        <h1>User {{ user_id }} Details</h1>
    {% endblock %}
    """
    )

    # Create typed parameter directory
    user_typed_dir = users_dir / "[id:uuid]"
    user_typed_dir.mkdir()

    (user_typed_dir / "layout.html").write_text(
        """
    {% extends "app/users/layout.html" %}
    {% block users_content %}
        <div class="user-uuid-layout">
            {% block user_detail_content %}{% endblock %}
        </div>
    {% endblock %}
    """
    )

    (user_typed_dir / "page.html").write_text(
        """
    {% extends "app/users/layout.html" %}
    {% block user_detail_content %}
        <h1>User UUID: {{ user_id }}</h1>
    {% endblock %}
    """
    )

    yield templates

    # Cleanup
    shutil.rmtree(templates)


@pytest.fixture
def application(template_dir) -> TestClient:
    api = CannulaApplication(start_path=template_dir)
    return TestClient(api)


def test_application(application: TestClient):
    slash = application.get("/")
    assert slash.status_code == 200, slash.text
    assert "ROOT" in slash.text

    not_found = application.get("/not_found")
    assert not_found.status_code == 404, not_found.text

    hidden = application.get("/_hidden")
    assert hidden.status_code == 404, hidden.text

    operation = application.get("/operation/Me?arg=anything")
    assert operation.status_code == 200, operation.text
    assert "Operation: Me" in operation.text

    users = application.get("/app/users/1234")
    assert users.status_code == 200, users.text

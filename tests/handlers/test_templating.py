import shutil
from pathlib import Path
from typing import Generator

import pytest
from starlette.testclient import TestClient

from cannula import CannulaAPI


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
    templates = tmp_path / "templates"
    templates.mkdir()

    # Create an operations file
    (templates / "operations.graphql").write_text(
        """
        query Me { me { name } }
    """
    )

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
def application(template_dir, valid_schema) -> TestClient:
    api = CannulaAPI(
        schema=valid_schema,
        app_directory=template_dir,
        operations=template_dir / "operations.graphql",
    )
    return TestClient(api)


def test_application(application: TestClient):
    not_found = application.get("/not_found")
    assert not_found.status_code == 404, not_found.text

    operation = application.get("/operation/Me?arg=anything")
    assert operation.status_code == 200, operation.text
    assert "Operation: Me" in operation.text

    users = application.get("/app/users/1234")
    assert users.status_code == 200, users.text

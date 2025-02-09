import shutil
from pathlib import Path
from typing import Generator

import pytest
from jinja2 import Environment

from cannula.handlers.templating import NextJSStyleLoader


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
    {% extends "../layout.html" %}
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
    {% extends "layout.html" %}
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
    {% extends "../layout.html" %}
    {% block app_content %}
        <div class="users-layout">
            {% block users_content %}{% endblock %}
        </div>
    {% endblock %}
    """
    )

    (users_dir / "page.html").write_text(
        """
    {% extends "layout.html" %}
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
    {% extends "../layout.html" %}
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
    {% extends "../layout.html" %}
    {% block users_content %}
        <div class="user-uuid-layout">
            {% block user_detail_content %}{% endblock %}
        </div>
    {% endblock %}
    """
    )

    (user_typed_dir / "page.html").write_text(
        """
    {% extends "layout.html" %}
    {% block user_detail_content %}
        <h1>User UUID: {{ user_id }}</h1>
    {% endblock %}
    """
    )

    print(templates)
    print([x for x in templates.glob("*.html")])
    yield templates

    # Cleanup
    shutil.rmtree(templates)


def test_root_layout(template_dir):
    """Test that root layout can be loaded directly"""
    env = Environment(loader=NextJSStyleLoader(template_dir))
    template = env.get_template("layout.html")
    rendered = template.render()
    assert "Root Layout" in rendered


def test_app_extends_root(template_dir):
    """Test that app layout extends root layout"""
    env = Environment(loader=NextJSStyleLoader(template_dir))
    template = env.get_template("/app/layout.html")
    rendered = template.render()
    assert "Root Layout" in rendered
    assert "App Nav" in rendered


def test_users_extends_app(template_dir):
    """Test that users layout extends app layout"""
    env = Environment(loader=NextJSStyleLoader(template_dir))
    template = env.get_template("/app/users/layout.html")
    rendered = template.render()
    assert "Root Layout" in rendered
    assert "App Nav" in rendered
    assert "users-layout" in rendered


def test_user_detail_extends_users(template_dir):
    """Test that user detail extends users layout"""
    env = Environment(loader=NextJSStyleLoader(template_dir))
    template = env.get_template("/app/users/[id]/page.html")
    rendered = template.render(user_id=123)
    assert "Root Layout" in rendered
    assert "users-layout" in rendered
    assert "user-detail-layout" in rendered
    assert "User 123 Details" in rendered


def test_relative_extends(template_dir):
    """Test that relative extends (../) work correctly"""
    env = Environment(loader=NextJSStyleLoader(template_dir))
    template = env.get_template("/app/users/[id]/page.html")
    rendered = template.render(user_id=123)
    assert "Root Layout" in rendered
    assert "users-layout" in rendered


def test_same_directory_extends(template_dir):
    """Test that extends finds layouts in the same directory first"""
    env = Environment(loader=NextJSStyleLoader(template_dir))
    template = env.get_template("/app/users/page.html")
    rendered = template.render()
    # Should use users/layout.html, not app/layout.html or root layout.html
    assert "users-layout" in rendered


def test_missing_template(template_dir):
    """Test that appropriate error is raised for missing templates"""
    env = Environment(loader=NextJSStyleLoader(template_dir))
    with pytest.raises(Exception):  # Replace with specific exception your loader raises
        env.get_template("/app/missing.html")


def test_typed_parameter_path(template_dir):
    """Test that template loader handles typed parameters like [id:uuid]"""
    env = Environment(loader=NextJSStyleLoader(template_dir))
    template = env.get_template("/app/users/[id:uuid]/page.html")
    rendered = template.render(user_id="123e4567-e89b-12d3-a456-426614174000")
    assert "Root Layout" in rendered
    assert "users-layout" in rendered
    assert "user-uuid-layout" in rendered
    assert "User UUID: 123e4567-e89b-12d3-a456-426614174000" in rendered


def test_outside_root_traversal(template_dir):
    """Test that template loader prevents traversal outside root directory"""
    env = Environment(loader=NextJSStyleLoader(template_dir))
    with pytest.raises(Exception):  # Replace with specific exception your loader raises
        env.get_template("../outside.html")

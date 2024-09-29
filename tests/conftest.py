import logging

LOG = logging.getLogger("cannula.tests")


logging.basicConfig(
    level=logging.DEBUG, filename="reports/test-report.log", filemode="w"
)


def pytest_runtest_setup(item):
    LOG.info("=======================================================")
    LOG.info(f"Running test: {item.name}")
    LOG.info("=======================================================")

import logging
import typing

import cannula

LOG = logging.getLogger(__name__)

COLORS = {
    'ComputeServers': 'rgb(54, 162, 235)',
    'Networks': 'rgb(54, 162, 235)',
    'Volumes': 'rgb(54, 162, 235)',
}

quota_resolver = cannula.Resolver(__name__)


class Dataset(typing.NamedTuple):
    used: int
    limit: int
    color: str
    label: str

    @property
    def data(self):
        remaining = self.limit - self.used
        return [self.used, remaining]

    @property
    def backgroundColor(self):
        return [self.color]


class QuotaData(typing.NamedTuple):
    label: str
    used: int
    limit: int
    color: str
    quota_label: str = 'Quota'

    @property
    def datasets(self):
        return [
            Dataset(
                used=self.used,
                limit=self.limit,
                color=self.color,
                label=f'{self.label} Quota'
            )
        ]

    @property
    def labels(self):
        return [self.label, self.quota_label]


@quota_resolver.resolver('Query')
async def quotaChartData(source, info, resource=None):
    if resource == 'ComputeServers':
        LOG.info(f'MARRIIIOOOO {resource}')
        server_quota = await info.context.ComputeServers.fetchLimits()

        return QuotaData(
            label="Servers",
            used=server_quota.used,
            limit=server_quota.limit,
            color=COLORS.get(resource)
        )

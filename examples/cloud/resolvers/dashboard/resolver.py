import asyncio
import itertools
import logging
import typing

import cannula

LOG = logging.getLogger(__name__)

COLORS = {
    "ComputeServers": "#cc65fe",
    "Networks": "#36a2eb",
    "Volumes": "#ff6384",
}

dashboard_resolver = cannula.Resolver(__name__)


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
    quota_label: str = "Quota"

    @property
    def datasets(self):
        return [
            Dataset(
                used=self.used,
                limit=self.limit,
                color=self.color,
                label=f"{self.label} Quota",
            )
        ]

    @property
    def labels(self):
        return [self.label, self.quota_label]


@dashboard_resolver.resolver("Query")
async def quotaChartData(source, info, resource):
    if resource == "ComputeServers":
        server_quota = await info.context.ComputeServers.fetchLimits()

        return QuotaData(
            label="Servers",
            used=server_quota.used,
            limit=server_quota.limit,
            color=COLORS.get(resource),
        )
    elif resource == "Networks":
        network_quota = await info.context.Network.fetchLimits()

        return QuotaData(
            label="Networks",
            used=network_quota.used,
            limit=network_quota.limit,
            color=COLORS.get(resource),
        )
    elif resource == "Volumes":
        volume_quota = await info.context.Volume.fetchLimits()

        return QuotaData(
            label="GB Used",
            used=volume_quota.absolute.totalGigabytesUsed,
            limit=volume_quota.absolute.maxTotalVolumeGigabytes,
            color=COLORS.get(resource),
            quota_label="GB Left",
        )


@dashboard_resolver.resolver("Query")
async def resources(source, info, region):
    servers = info.context.ComputeServers.fetchServers(region)
    networks = info.context.Network.fetchNetworks(region)
    volumes = info.context.Volume.fetchVolumes(region)

    results = await asyncio.gather(servers, networks, volumes)
    # results is a list of lists [[results], [results], [results]]
    return itertools.chain(*results)

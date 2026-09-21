"""Typed models for the Admin V2 dashboard API and aggregators."""

from __future__ import annotations

from pydantic import Field

from hiddifypanel.panel.commercial.restapi.v2.pydantic_schema import ApiModel

DEFAULT_RANGE_DAYS = 30


class ChildUsagePoint(ApiModel):
    usage: int = 0
    online: int = 0


class DashboardDailyPoint(ApiModel):
    date: str
    usage: int = 0
    online: int = 0
    by_child: dict[int, ChildUsagePoint] | None = None


class UsageTotals(ApiModel):
    today: int = 0
    yesterday: int = 0
    week: int = 0
    month: int = 0
    total: int = 0


class UsageAverages(ApiModel):
    daily_week: int = 0
    daily_month: int = 0


class UsagePrevious(ApiModel):
    week: int = 0
    month: int = 0


class UsageTrends(ApiModel):
    day: float | None = None
    week: float | None = None
    month: float | None = None


class UsagePeak(ApiModel):
    date: str
    usage: int


class DashboardUsage(ApiModel):
    totals: UsageTotals = Field(default_factory=UsageTotals)
    averages: UsageAverages = Field(default_factory=UsageAverages)
    previous: UsagePrevious = Field(default_factory=UsagePrevious)
    trends: UsageTrends = Field(default_factory=UsageTrends)
    peak: UsagePeak | None = None


class UsageSummary(ApiModel):
    series: list[DashboardDailyPoint] = Field(default_factory=list)
    totals: UsageTotals = Field(default_factory=UsageTotals)
    averages: UsageAverages = Field(default_factory=UsageAverages)
    previous: UsagePrevious = Field(default_factory=UsagePrevious)
    trends: UsageTrends = Field(default_factory=UsageTrends)
    peak: UsagePeak | None = None

    def to_usage(self) -> DashboardUsage:
        return DashboardUsage(
            totals=self.totals,
            averages=self.averages,
            previous=self.previous,
            trends=self.trends,
            peak=self.peak,
        )


class UsersOnline(ApiModel):
    m5: int = 0
    h24: int = 0
    today: int = 0
    yesterday: int = 0
    week: int = 0
    month: int = 0


class UsersAverages(ApiModel):
    daily_week: int = 0
    daily_month: int = 0


class DashboardUsers(ApiModel):
    total: int = 0
    enabled: int = 0
    online: UsersOnline = Field(default_factory=UsersOnline)
    averages: UsersAverages = Field(default_factory=UsersAverages)


class DashboardNode(ApiModel):
    id: int
    name: str
    mode: str


class DashboardStats(ApiModel):
    range_days: int = DEFAULT_RANGE_DAYS
    series: list[DashboardDailyPoint] = Field(default_factory=list)
    usage: DashboardUsage = Field(default_factory=DashboardUsage)
    users: DashboardUsers = Field(default_factory=DashboardUsers)
    nodes: list[DashboardNode] = Field(default_factory=list)


class DashboardCpu(ApiModel):
    percent: float = 0.0
    per_core: list[float] = Field(default_factory=list)
    cores: int = 0
    load_avg: list[float] = Field(default_factory=list)
    load_percent: list[float] = Field(default_factory=list)


class DashboardMemory(ApiModel):
    used_gb: float = 0.0
    total_gb: float = 0.0
    available_gb: float = 0.0
    cached_gb: float = 0.0
    percent: float = 0.0
    swap_used_gb: float = 0.0
    swap_total_gb: float = 0.0
    swap_percent: float = 0.0


class DashboardDisk(ApiModel):
    used_gb: float = 0.0
    total_gb: float = 0.0
    free_gb: float = 0.0
    percent: float = 0.0
    hiddify_gb: float | None = None


class DiskFolderUsage(ApiModel):
    name: str
    path: str
    size_gb: float = 0.0


class DashboardDiskDetail(ApiModel):
    node_id: int = 0
    disk: DashboardDisk = Field(default_factory=DashboardDisk)
    top_folders: list[DiskFolderUsage] = Field(default_factory=list)
    error: str | None = None


class DashboardNetwork(ApiModel):
    bytes_sent: int = 0
    bytes_recv: int = 0
    sent_gb: float = 0.0
    recv_gb: float = 0.0
    total_gb: float = 0.0
    sampled_at: float = 0.0
    connections: int = 0
    unique_ips: int = 0


class DashboardHost(ApiModel):
    hostname: str = ""
    boot_time: float = 0.0
    uptime_s: int = 0
    panel_version: str | None = None


class DashboardProcess(ApiModel):
    name: str
    percent: float = 0.0
    memory_gb: float | None = None
    cpu_percent: float | None = None
    path: str | None = None


class DashboardProcesses(ApiModel):
    count: int = 0
    cpu: list[DashboardProcess] = Field(default_factory=list)
    memory: list[DashboardProcess] = Field(default_factory=list)


class DashboardSystem(ApiModel):
    cpu: DashboardCpu = Field(default_factory=DashboardCpu)
    memory: DashboardMemory = Field(default_factory=DashboardMemory)
    disk: DashboardDisk = Field(default_factory=DashboardDisk)
    network: DashboardNetwork = Field(default_factory=DashboardNetwork)
    host: DashboardHost = Field(default_factory=DashboardHost)


class MetricsSnapshot(ApiModel):
    cpu: DashboardCpu
    memory: DashboardMemory
    disk: DashboardDisk
    network: DashboardNetwork
    host: DashboardHost
    processes: DashboardProcesses

    def with_panel_version(self, version: str) -> MetricsSnapshot:
        return self.model_copy(update={"host": self.host.model_copy(update={"panel_version": version})})


class DashboardNodeStats(ApiModel):
    id: int
    name: str
    mode: str
    ok: bool = True
    error: str | None = None
    cpu: DashboardCpu | None = None
    memory: DashboardMemory | None = None
    disk: DashboardDisk | None = None
    network: DashboardNetwork | None = None
    host: DashboardHost | None = None
    processes: DashboardProcesses = Field(default_factory=DashboardProcesses)

    def system(self) -> DashboardSystem:
        return DashboardSystem(
            cpu=self.cpu or DashboardCpu(),
            memory=self.memory or DashboardMemory(),
            disk=self.disk or DashboardDisk(),
            network=self.network or DashboardNetwork(),
            host=self.host or DashboardHost(),
        )


class NodeSystemCollection(ApiModel):
    system: DashboardSystem = Field(default_factory=DashboardSystem)
    processes: DashboardProcesses = Field(default_factory=DashboardProcesses)
    node_stats: list[DashboardNodeStats] = Field(default_factory=list)


class DashboardOutputSchema(ApiModel):
    generated_at: str = Field(default="", description="ISO timestamp of this snapshot")
    range_days: int = Field(default=DEFAULT_RANGE_DAYS, description="Number of days in the usage series")
    series: list[DashboardDailyPoint] = Field(default_factory=list, description="Daily usage/online history (oldest first)")
    usage: DashboardUsage = Field(default_factory=DashboardUsage, description="Usage totals, averages, previous periods and trends")
    users: DashboardUsers = Field(default_factory=DashboardUsers, description="User counts and online buckets")
    system: DashboardSystem = Field(default_factory=DashboardSystem, description="CPU, memory, disk, network and host metrics")
    processes: DashboardProcesses = Field(default_factory=DashboardProcesses, description="Top processes by CPU and memory")
    nodes: list[DashboardNode] = Field(default_factory=list, description="Selectable nodes (parent DB)")
    node_stats: list[DashboardNodeStats] = Field(default_factory=list, description="Live system stats per node")
    child_id: int | None = Field(default=None, description="Selected node id, null means all")

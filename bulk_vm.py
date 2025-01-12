from typing import Protocol
import netaddr
import csv
from dcim.choices import InterfaceTypeChoices, InterfaceModeChoices
from dcim.models import Platform, DeviceRole, Site, Interface
from ipam.models import IPAddress, VRF, Prefix, VLAN, Service
from tenancy.models import Tenant
from virtualization.models import VirtualMachine, Cluster, VMInterface
from virtualization.choices import VirtualMachineStatusChoices
from extras.scripts import Script, TextVar, ChoiceVar, ObjectVar
from extras.models import Tag
from utilities.forms import APISelect
from django.contrib.contenttypes.models import ContentType


class VM:

    status: str
    tenant: Tenant
    cluster: Cluster
    site: Site
    csv_ip_address: str
    ip_address: IPAddress
    comment: str

    DEFAULT_TAGS = ['ansible', 'zero_day']
    DEFAULT_DOMAIN_PRIVATE = 'patientsky.zone'
    DEFAULT_DOMAIN_PUBLIC = 'patientsky.dev'
    DEFAULT_PROM_ALERT_TYPE = '24-7-devops'

    PROMETHEUS_DICT = dict(
        cph1=dict(
            env_dev=dict(prom_env="dev"),
            env_cmi=dict(prom_env="cph-migration"),
            env_cse=dict(prom_env="cph-secure"),
            env_dmo=dict(prom_env="demo"),
            env_inf=dict(prom_env="cph-inf"),
            env_qua=dict(prom_env="qa"),
            env_tst=dict(prom_env="tst"),
        ),
        cph2=dict(
            env_pmpdev=dict(prom_env="cph2-pmpdev"),
            env_pltdev=dict(prom_env="cph2-pltdev"),
            env_inf=dict(prom_env="cph2-inf"),
            env_dev=dict(prom_env="cph2-dev"),
            env_qua=dict(prom_env="cph2-qua"),
            env_stg=dict(prom_env="cph2-stg"),
            env_tst=dict(prom_env="cph2-tst"),
            env_prod=dict(prom_env="cph2-prod"),
        ),
        sto1=dict(
            env_inf=dict(prom_env="sto1"),
            env_pee=dict(prom_env="pee"),
            env_pfi=dict(prom_env="pfi"),
            env_ppt=dict(prom_env="ppt"),
            env_tst=dict(prom_env="sto1"),
        ),
        osl1=dict(
            env_dev=dict(prom_env="psno"),
            env_inf=dict(prom_env="infrastructure"),
            env_plt=dict(prom_env="psno"),
            env_pno=dict(prom_env="psno"),
            env_ppt=dict(prom_env="ppt"),
        ),
        osl2=dict(
            env_dev=dict(prom_env="dev"),
            env_qa=dict(prom_env="qa"),
            env_inf=dict(prom_env="inf"),
            env_tst=dict(prom_env="tst"),
            env_stg=dict(prom_env="stg"),
            env_dmo=dict(prom_env="dmo"),
            env_mig=dict(prom_env="mig"),
            env_sandbox=dict(prom_env="sandbox"),
            env_psno=dict(prom_env="psno"),
            env_pno=dict(prom_env="psno"),
        ),
        aeu1=dict(
            env_inf=dict(prom_env="aeu1-inf"),
        )
    )

    def __init__(self, status, tenant, cluster, prom_alert_type, datazone, env, platform, role, backup, backup_offsite, vcpus, memory, disk, ip_address, hostname, extra_tags):
        # IP address can first be created after vm
        self.csv_ip_address = ip_address
        self.set_cluster(cluster)
        self.set_prom_alert_type(prom_alert_type)
        self.set_status(status)
        self.set_tenant(tenant)
        self.set_datazone(datazone)
        self.set_env(env)
        self.set_platform(platform)
        self.set_role(role)
        self.set_backup_tag(backup)
        self.set_backup_offsite_tag(backup_offsite)
        self.set_vcpus(vcpus)
        self.set_memory(memory)
        self.set_disk(disk)
        self.set_hostname(hostname)
        self.set_vlan(None)
        self.set_extra_tags(extra_tags)
        self.set_comments()

    def set_comments(self):
        try:
            extra_tags = ""
            for tag in self.extra_tags:
                extra_tags += tag + ","

            if self.backup_offsite is not None:
                self.comments = "status,tenant,cluster,prom_alert_type,datazone,env,platform,role,backup,backup_offsite,vcpus,memory,disk,hostname,ip_address,extra_tags\n"
                self.comments += "{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},\"{15}\"".format(
                    self.status,
                    self.tenant.slug,
                    self.cluster,
                    self.prom_alert_type,
                    self.datazone.name.split('datazone_')[1],
                    self.env.name.split('env_')[1],
                    self.platform,
                    self.role,
                    self.backup.name,
                    self.backup_offsite.name if self.backup_offsite is not None else "",
                    self.vcpus,
                    self.memory,
                    self.disk,
                    self.hostname,
                    self.csv_ip_address,
                    extra_tags[:-1],
                )
            else:
                self.comments = "status,tenant,cluster,prom_alert_type,datazone,env,platform,role,backup,vcpus,memory,disk,hostname,ip_address,extra_tags\n"
                self.comments += "{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},\"{14}\"".format(
                    self.status,
                    self.tenant.slug,
                    self.cluster,
                    self.prom_alert_type,
                    self.datazone.name.split('datazone_')[1],
                    self.env.name.split('env_')[1],
                    self.platform,
                    self.role,
                    self.backup.name,
                    self.vcpus,
                    self.memory,
                    self.disk,
                    self.hostname,
                    self.csv_ip_address,
                    extra_tags[:-1],
                )

        except Exception as e:
            raise Exception("Comments - {0}".format(e))

    def set_prom_alert_type(self, prom_alert_type):
        try:
            self.prom_alert_type = prom_alert_type if prom_alert_type is not None else self.DEFAULT_PROM_ALERT_TYPE
        except Exception as e:
            raise Exception("Prometheus alert_type - {0}".format(e))

    def set_extra_tags(self, extra_tags):
        try:
            if extra_tags is None:
                self.extra_tags = extra_tags
            else:
                self.extra_tags = extra_tags.split(',')
        except Exception as e:
            raise Exception("Extra tags - {0}".format(e))

    def set_vlan(self, vlan):
        try:
            self.vlan = VLAN.objects.get(
                vid=vlan,
                site=self.site
            )
        except Exception:
            self.vlan = None

    def generate_hostname(self):
        # I now proclaim this VM, First of its Name, Queen of the Andals and the First Men, Protector of the Seven Kingdoms
        vm_index = "001"
        vm_search_for = "{0}-{1}-{2}-".format(self.site.slug, self.env.name.split('_')[1], self.role.name.split(':')[0])
        vms = VirtualMachine.objects.filter(
            name__startswith=vm_search_for
        )
        if len(vms) > 0:
            # Get last of its kind
            last_vm_index = int(vms[len(vms) - 1].name.split('-')[3]) + 1
            if last_vm_index < 10:
                vm_index = '00' + str(last_vm_index)
            elif last_vm_index < 100:
                vm_index = '0' + str(last_vm_index)
            else:
                vm_index = str(last_vm_index)

        return "{0}{1}".format(vm_search_for, vm_index)

    def get_vrf(self):
        return VRF.objects.get(
            name="global"
        )

    def get_fqdn(self):
        return "{}.{}".format(self.hostname, self.DEFAULT_DOMAIN_PRIVATE if netaddr.IPNetwork(self.ip_address.address).is_private() is True else self.DEFAULT_DOMAIN_PUBLIC)

    def set_ip_address(self, vm):
        try:
            ip_check = IPAddress.objects.filter(address=self.csv_ip_address)
            if len(ip_check) > 0:
                raise Exception(str(ip_check[0].address) + ' is already assigned')
            if not isinstance(self.vlan, VLAN):
                self.ip_address = IPAddress(
                    address=self.csv_ip_address,
                    vrf=self.get_vrf(),
                    tenant=self.tenant,
                )
            else:
                # Auto assign IPs from vlan
                prefix = Prefix.objects.get(
                    vlan=self.vlan,
                    site=vm.site
                )
                prefix.is_pool = True
                # Save as pool
                prefix.save()

                ip_address = prefix.get_first_available_ip()
                self.ip_address = IPAddress(
                    address=ip_address,
                    vrf=self.get_vrf(),
                    tenant=self.tenant,
                )
            self.ip_address.dns_name = self.get_fqdn()
            self.ip_address.save()

        except Exception as e:
            self.ip_address = None
            raise Exception("IP address - {0}".format(e))

    def get_vlan(self):
        return False

    def set_hostname(self, hostname):
        try:
            self.hostname = hostname if hostname is not None else self.generate_hostname()
        except Exception as e:
            raise Exception("Hostname - {0}".format(e))

    def set_disk(self, disk):
        try:
            self.disk = disk
        except Exception as e:
            raise Exception("Disk - {0}".format(e))

    def set_memory(self, memory):
        try:
            self.memory = memory
        except Exception as e:
            raise Exception("Memory - {0}".format(e))

    def set_vcpus(self, vcpus):
        try:
            self.vcpus = vcpus
        except Exception as e:
            raise Exception("vcpus - {0}".format(e))

    def set_backup_tag(self, backup):
        try:
            if isinstance(backup, Tag):
                self.backup = backup
            else:
                self.backup = Tag.objects.filter(name="{0}".format(backup))[0]
        except Exception as e:
            raise Exception("Tag backup {0} does not exist, {1}".format(backup, e))

    def set_backup_offsite_tag(self, backup_offsite):
        try:
            if isinstance(backup_offsite, Tag):
                self.backup_offsite = backup_offsite
            else:
                self.backup_offsite = Tag.objects.filter(name="{0}".format(backup_offsite))[0]
        except Exception:
            self.backup_offsite = None

    def set_site(self, site):
        try:
            if isinstance(site, Site):
                self.site = site
            else:
                raise Exception("site is not of instance 'Site'")
        except Exception as e:
            raise Exception('Site does not exist - ' + str(e))

    def set_role(self, role):
        try:
            self.role = DeviceRole.objects.get(
                name=role
            )
        except Exception as e:
            raise Exception('Role does not exist - ' + str(e))

    def set_platform(self, platform):
        try:
            if isinstance(platform, Platform):
                self.platform = platform
            else:
                self.platform = Platform.objects.get(
                    name=platform
                )
        except Exception as e:
            raise Exception("Platform does not exist {0}".format(e))

    def set_env(self, env):
        try:
            if isinstance(env, Tag):
                self.env = env
            else:
                self.env = Tag.objects.get(name="env_{0}".format(env))
        except Exception as e:
            raise Exception("Tag env does not exist! - {0}".format(e))

    def set_datazone(self, datazone):
        try:
            self.datazone = Tag.objects.get(name="datazone_{0}".format(datazone))
        except Exception as e:
            raise Exception("Tag datazone does not exist! - {0}".format(e))

    def set_cluster(self, cluster):
        try:
            if isinstance(cluster, Cluster):
                self.cluster = cluster
            else:
                self.cluster = Cluster.objects.get(
                    name=cluster
                )
            self.set_site(self.cluster.site)
        except Exception as e:
            raise Exception("Cluster does not exist {0}".format(e))

    def set_tenant(self, tenant):
        try:
            if isinstance(tenant, Tenant):
                self.tenant = tenant
            else:
                self.tenant = Tenant.objects.get(
                    slug=tenant
                )
        except Exception as e:
            raise Exception("Tenant does not exist {0}".format(e))

    def set_status(self, status):
        try:
            self.status = VirtualMachineStatusChoices.STATUS_STAGED if status == 'staged' else VirtualMachineStatusChoices.STATUS_PLANNED
        except Exception as e:
            raise Exception("Status does not exist {0}".format(e))

    def get_ip_address(self):
        return self.ip_address

    def __create_ip_address(self, vm):
        self.set_ip_address(vm)
        vm.primary_ip4 = self.get_ip_address()
        vm.save()

    def __create_tags(self, vm: VirtualMachine):
        vm.tags.add(self.datazone)
        vm.tags.add(self.env)
        vm.tags.add(self.backup)
        if(self.backup_offsite is not None):
            vm.tags.add(self.backup_offsite)
        for tag in self.DEFAULT_TAGS:
            vm.tags.add(tag)
        if self.extra_tags is not None:
            for tag in self.extra_tags:
                vm.tags.add(tag)
        vm.save()
        self.set_tags(vm.tags)

    def set_tags(self, tags):
        self.tags = tags

    def get_tags(self):
        list = []
        for tag in self.tags.all():
            list.append(tag.name)
        return list

    def __create_vm(self):
        vm = VirtualMachine(
            status=self.status,
            cluster=self.cluster,
            platform=self.platform,
            role=self.role,
            tenant=self.tenant,
            name=self.hostname,
            disk=self.disk,
            memory=self.memory,
            vcpus=self.vcpus,
            comments=self.comments,
        )
        vm.save()
        return vm

    def __create_interface(self, vm: VirtualMachine):
        """
        Setup interface and add IP address
        """
        try:

            # Get net address tools
            ip = netaddr.IPNetwork(vm.primary_ip4.address)
            prefix_search = str(ip.network) + '/' + str(ip.prefixlen)

            prefix = Prefix.objects.get(
                prefix=prefix_search,
                is_pool=True,
                site=self.site,
            )

            interfaces = vm.get_config_context().get('interfaces')

            interface = VMInterface(
                name=interfaces['nic0']['name'],
                mtu=interfaces['nic0']['mtu'],
                virtual_machine=vm
            )

            # If we need anything other than Access, here is were to change it
            if interfaces['nic0']['mode'] == "Access":
                interface.mode = InterfaceModeChoices.MODE_ACCESS
                interface.untagged_vlan = prefix.vlan

            interface.save()

            type = ContentType.objects.get(app_label="virtualization", model="vminterface")
            self.ip_address.assigned_object_type = type
            self.ip_address.assigned_object_id = interface.id
            self.ip_address.assigned_object = interface
            self.ip_address.save()

        except Exception as e:
            raise Exception("Error while creating interface - {0}".format(e))
        return True

    def __prometheus_env_translator(self, env: Tag, site: Site):
        try:
            return self.PROMETHEUS_DICT[site.name][env.name].get('prom_env')
        except Exception as e:
            raise Exception("Error while translating prometheus env - error: {0} env: {1} site: {2}".format(e, env, site))

    def __create_service(self, vm):

        try:

            services = vm.get_config_context().get('prometheus_exporters')

            for name in services:
                s = Service(
                    name=name,
                    virtual_machine_id=vm.id,
                    ports=services[name].get('ports'),
                    protocol=services[name].get('protocol'),
                )
                s.custom_field_data["prom_location"] = vm.site.slug
                s.custom_field_data["prom_env"] = self.__prometheus_env_translator(site=self.site, env=self.env)
                s.custom_field_data["prom_class"] = self.role.name
                s.custom_field_data["prom_alert_type"] = self.prom_alert_type
                s.custom_field_data["prom_metrics_path"] = services[name].get('metrics_path')
                s.custom_field_data["prom_ignore"] = False

                s.save()

                # Set ip address
                s.ipaddresses.add(vm.primary_ip4.id)
                for tag in services[name].get('tags'):
                    s.tags.add(Tag.objects.filter(name="{0}".format(tag))[0])
                s.save()

        except Exception as e:
            raise Exception("Error while creating service - {0} {1}".format(e, vm))
        return True

    def create(self):
        try:
            vm = self.__create_vm()
            self.__create_ip_address(vm)
            self.__create_tags(vm)
            self.__create_interface(vm)
            self.__create_service(vm)
        except Exception as e:
            raise e
        return True


class BulkDeployVM(Script):
    """
    Example CSV full:
    status,tenant,cluster,datazone,env,platform,role,backup,vcpus,memory,disk,hostname,ip_address,extra_tags
    staged,patientsky-hosting,odn1,1,vlb,base:v1.0.0-coreos,redirtp:v0.2.0,backup_nobackup,1,1024,10,odn1-vlb-redirtp-001,10.50.61.10/24,"voip,test_tag,cluster_id_voip_galera_001"
    staged,patientsky-hosting,odn1,1,vlb,base:v1.0.0-coreos,consul:v1.0.1,backup_general_1,2,2048,20,odn1-vlb-consul-001,10.50.61.11/24,"voip,test_tag,cluster_id_voip_galera_002"
    staged,patientsky-hosting,odn1,1,vlb,base:v1.0.0-coreos,rediast:v0.2.0,backup_general_4,4,4096,30,odn1-vlb-rediast-001,10.50.61.12/24,"voip,test_tag,cluster_id_voip_galera_003"

    Example CSV minimal (If all defaults are set):
    vcpus,memory,disk,ip_address,extra_tags
    1,1024,10,10.50.61.10/24,"voip,test_tag,cluster_id_voip_galera_001"
    2,2048,20,10.50.61.11/24,"voip,test_tag,cluster_id_voip_galera_002"
    4,4096,30,10.50.61.12/24,"voip,test_tag,cluster_id_voip_galera_003"

    ** Required Params **
    Param: cluster          - vSphere cluster name
    Param: env              - Adds 'env_xxx' tag
    Param: platform         - VM Platform e.g base:v1.0.0-coreos
    Param: backup           - Adds backup tag
    Param: backup_offsite   - Adds offsite backup tag
    Param: vcpus            - Virtual CPUs (hot add)
    Param: memory           - Virtual memory (hot add)
    Param: disk             - Disk2 size
    Param: hostname         - VM hostname (Optional if 'role' is set)
    Param: role             - VM Device role
    Param: ip_address       - VM IP address

    ** Optional Params **
    Param: status       - VM status (default 'staged')
    Param: tenant       - Netbox tenant (default slug:'patientsky-hosting')
    Param: datazone     - Adds 'datazone_x' tag (default 'rr')
    Param: extra_tags   - Adds extra tags to VM
    """

    DEFAULT_CSV_FIELDS = "vcpus,memory,disk,ip_address,extra_tags"
    datazone_rr: bool = True

    class Meta:
        name = "Bulk deploy new VMs"
        description = "Deploy new virtual machines from existing platforms"
        fields = ['vms', 'default_status', 'default_tenant', 'default_datazone', 'default_backup', 'default_backup_offsite', 'default_role', 'default_prom_alert_type']
        field_order = ['vms', 'default_prom_alert_type', 'default_status', 'default_tenant', 'default_datazone', 'default_backup', 'default_backup_offsite', 'default_role']
        commit_default = False

    vms = TextVar(
        label="Import CSV",
        description="CSV data",
        required=True,
        default=DEFAULT_CSV_FIELDS
    )

    default_status = ChoiceVar(
        label="Default Status",
        description="Default VM `status`",
        required=False,
        choices=(
            (VirtualMachineStatusChoices.STATUS_STAGED, 'Staged (Deploy now)'),
            (VirtualMachineStatusChoices.STATUS_PLANNED, 'Planned (Save for later)')
        )
    )

    default_tenant = ObjectVar(
        model=Tenant,
        label="Default Tenant",
        default=1,
        required=False,
        description="Default CSV field `tenant` if none given",
    )

    default_datazone = ChoiceVar(
        label="Default Datazone",
        description="Default datazone",
        default="rr",
        required=False,
        choices=(
            ('rr', 'Round robin (1,2)'),
            ('1', '1'),
            ('2', '2')
        )
    )

    default_prom_alert_type = ChoiceVar(
        label="Default Alert Type",
        description="Default CSV field `prom_alert_type` if none given",
        default="24-7-devops",
        required=False,
        choices=(
            ('24-7-devops', '24-7-devops'),
            ('37-5-devops', '37-5-devops'),
            ('24-7-voip', '24-7-voip'),
            ('37-5-voip', '37-5-voip'),
        )
    )

    default_cluster = ObjectVar(
        model=Cluster,
        label="Default Cluster",
        description="Default CSV field `cluster` if none given",
        required=False,
    )

    default_env = ObjectVar(
        model=Tag,
        label="Default Environment",
        description="Default CSV field `env` if none given",
        required=False,
        query_params={
            'name__isw': 'env_'
        }
    )

    default_platform = ObjectVar(
        model=Platform,
        label="Default Platform",
        description="Default CSV field `platform` if none given",
        required=False,
        query_params=dict(
            name__isw=("flat", "ubuntu", "core"),
        )
    )

    default_role = ObjectVar(
        model=DeviceRole,
        label="Default Role",
        description="Default CSV field `role` if none given",
        default=None,
        required=False,
        query_params={
            'vm_role': True
        }
    )

    default_backup = ObjectVar(
        model=Tag,
        label="Default Backup",
        description="Default CSV field `backup` if none given",
        required=False,
        query_params=dict(
            name__nic='offsite',
            name__isw='backup'
        )
    )

    default_backup_offsite = ObjectVar(
        model=Tag,
        label="Default Offsite Backup",
        description="Default CSV field `backup_offsite` if none given",
        required=False,
        query_params=dict(
            name__ic='offsite'
        )
    )

    def get_vm_data(self):
        return self.vm_data

    def set_csv_data(self, vms):
        self.csv_raw_data = csv.DictReader(vms, delimiter=',')

    def get_csv_raw_data(self):
        return self.csv_raw_data

    def set(self, data):
        self.set_csv_data(data['vms'].splitlines())

    def get_datazone(self, datazone):
        if datazone == 'rr':
            datazone = 1 if self.datazone_rr else 2
            self.datazone_rr = not self.datazone_rr
        return datazone

    def run(self, data, commit):

        # Set data from raw csv
        self.set(data)
        line = 1
        for raw_vm in self.get_csv_raw_data():
            try:
                vm = VM(
                    status=raw_vm.get('status') if raw_vm.get('status') is not None else data['default_status'],
                    tenant=raw_vm.get('tenant') if raw_vm.get('tenant') is not None else data['default_tenant'],
                    datazone=raw_vm.get('datazone') if raw_vm.get('datazone') is not None else self.get_datazone(data['default_datazone']),
                    cluster=raw_vm.get('cluster') if raw_vm.get('cluster') is not None else data['default_cluster'],
                    prom_alert_type=raw_vm.get('prom_alert_type') if raw_vm.get('prom_alert_type') is not None else data['default_prom_alert_type'],
                    env=raw_vm.get('env') if raw_vm.get('env') is not None else data['default_env'],
                    platform=raw_vm.get('platform') if raw_vm.get('platform') is not None else data['default_platform'],
                    role=raw_vm.get('role') if raw_vm.get('role') is not None else data['default_role'],
                    backup=raw_vm.get('backup') if raw_vm.get('backup') is not None else data['default_backup'],
                    backup_offsite=raw_vm.get('backup_offsite') if raw_vm.get('backup_offsite') is not None else data['default_backup_offsite'],
                    vcpus=raw_vm.get('vcpus'),
                    memory=raw_vm.get('memory'),
                    disk=raw_vm.get('disk'),
                    hostname=raw_vm.get('hostname'),
                    ip_address=raw_vm.get('ip_address'),
                    extra_tags=raw_vm.get('extra_tags')
                )
                vm.create()
                self.log_success(
                    "{} `{}` for `{}`, `{}`, in cluster `{}`, env `{}`, datazone `{}`, backup `{}`".
                    format(
                        vm.status.capitalize(),
                        vm.hostname,
                        vm.tenant,
                        vm.ip_address.address,
                        vm.cluster,
                        str(vm.env.name).split('_')[1],
                        vm.datazone,
                        vm.backup,
                    )
                )
                line += 1
            except Exception as e:
                self.log_failure("Error in CSV line {0}, while creating VM \n`{1}` data \n`{2}`".format(line, e, raw_vm))
        return data['vms']

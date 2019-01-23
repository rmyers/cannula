import logging
import random
import uuid
from datetime import datetime
from datetime import timedelta

from bottle import request
from bottle import response
from bottle import route
from bottle import run

logging.basicConfig(level=logging.DEBUG)

LOG = logging.getLogger('mock-openstack')


HOST = "openstack"
PORT = "8080"
MIMIC_URL = f"http://{HOST}:{PORT}"
COMPUTE_URL = f"{MIMIC_URL}/nova/v2.1/{{project_id}}"
NEUTRON_URL = f"{MIMIC_URL}/neutron"
CINDER_URL = f"{MIMIC_URL}/cinder/v2/{{project_id}}"
KEYSTONE_V3 = f"{MIMIC_URL}/v3"
SERVERS = dict()
ACCOUNTS = dict()
TENANTS = dict()
USERS = dict()
SERVER_IDS = ["server3", "server2", "server1"]
ADJECTIVES = [
  'imminent',
  'perfect',
  'organic',
  'elderly',
  'dapper',
  'reminiscent',
  'mysterious',
  'trashy',
  'workable',
  'flaky',
  'offbeat',
  'spooky',
  'thirsty',
  'stereotyped',
  'wild',
  'devilish',
  'quarrelsome',
  'dysfunctional',
]
NOUNS = [
  'note',
  'yak',
  'hammer',
  'cause',
  'price',
  'quill',
  'truck',
  'glass',
  'color',
  'ring',
  'trees',
  'window',
  'letter',
  'seed',
  'sponge',
  'pie',
  'mass',
  'table',
  'plantation',
  'battle',
]


def name():
    """Generate a random name"""
    return f'{random.choice(ADJECTIVES)} {random.choice(NOUNS)}'


def get_id():
    """Generate a new uuid for id's"""
    return str(uuid.uuid4())


def get_ip():
    """Generate a random ip"""
    def bit():
        return random.randint(0, 255)
    return f'{bit()}.{bit()}.{bit()}.{bit()}'


def catalog(project_id):
    compute_url = COMPUTE_URL.format(project_id=project_id)
    neutron_url = NEUTRON_URL.format(project_id=project_id)
    cinder_url = CINDER_URL.format(project_id=project_id)
    return [
        {
            "endpoints": [
                {
                    "url": compute_url,
                    "interface": "public",
                    "region": "us-east",
                    "region_id": "us-east",
                    "id": "41e9e3c05091494d83e471a9bf06f3ac"
                },
                {
                    "url": compute_url,
                    "interface": "public",
                    "region": "us-west",
                    "region_id": "us-west",
                    "id": "4ad8904c486c407b9ebbc379c58ea432"
                }
            ],
            "type": "compute",
            "id": "4a1bd1ae55854833870ad35fdf1f9be1",
            "name": "nova"
        },
        {
            "endpoints": [
                {
                    "url": neutron_url,
                    "interface": "public",
                    "region": "us-east",
                    "region_id": "us-east",
                    "id": "c5a338861d2b4a609be30fdbf189b5c7"
                },
                {
                    "url": neutron_url,
                    "interface": "public",
                    "region": "us-west",
                    "region_id": "us-west",
                    "id": "dd3877984b2e4d49a951aa376c7580b2"
                }
            ],
            "type": "network",
            "id": "d78d372c287a4681a0003819c0f97177",
            "name": "neutron"
        },
        {
            "endpoints": [
                {
                    "url": cinder_url,
                    "interface": "public",
                    "region": "us-east",
                    "region_id": "us-east",
                    "id": "8861d2c5a33b4a609be30fdbf189b5c7"
                },
                {
                    "url": cinder_url,
                    "interface": "public",
                    "region": "us-west",
                    "region_id": "us-west",
                    "id": "2e4d49a9dd3877984b51aa376c7580b2"
                }
            ],
            "type": "volume",
            "id": "000381d78d372c287a4681a9c0f97177",
            "name": "cinder"
        }
    ]


def expires():
    now = datetime.utcnow()
    expires = now + timedelta(hours=2)
    expires_at = "{0}Z".format(expires.isoformat())
    issued_at = "{0}Z".format(now.isoformat())
    return {
        'expires': expires_at,
        'issued': issued_at,
    }


@route('/v3')
def v3():
    return {
        "version": {
            "status": "stable",
            "updated": "2016-04-04T00:00:00Z",
            "media-types": [
                {
                    "base": "application/json",
                    "type": "application/vnd.openstack.identity-v3+json"
                }
            ],
            "id": "v3.6",
            "links": [
                {
                    "href": KEYSTONE_V3,
                    "rel": "self"
                }
            ]
        }
    }


@route('/v3/auth/catalog', method='GET')
def v3_catalog():
    auth_token = request.headers.get('X-Auth-Token')
    _, project_id = auth_token.split(':')
    _catalog = catalog(project_id)
    return {
        "catalog": _catalog
    }


@route('/v3/auth/tokens', method='POST')
def v3_auth_tokens():
    LOG.info('Identity Log Request')
    user = request.json['auth']['identity']['password']['user']['name']
    project_id = USERS.get(user)
    if project_id is None:
        project_id = get_id()
        USERS[user] = project_id
    ex = expires()
    _catalog = catalog(project_id)
    response.status = 201
    resp = {
        "token": {
            "methods": ["password"],
            "roles": [
                {
                    "id": get_id(),
                    "name": "admin",
                }
            ],
            "expires_at": ex['expires'],  # "2017-01-17T05:20:17.000000Z",
            "project": {
                "domain": {
                    "id": "default",
                    "name": "Default"
                },
                "id": project_id,
                "name": "admin"
            },
            "catalog": _catalog,
            "user": {
                "domain": {
                    "id": "default",
                    "name": "Default"
                },
                "id": get_id(),
                "name": user
            },
            "audit_ids": [
                "DriuAdgyRoWcZG95-qpakw"
            ],
            "issued_at": ex['issued'],
        }
    }
    response.set_header('X-Subject-Token', f'{user}:{project_id}')
    return resp


IMAGES = [
    {
        "status": "ACTIVE",
        "updated": "2016-12-05T22:30:29Z",
        "id": get_id(),
        "OS-EXT-IMG-SIZE:size": 260899328,
        "name": name(),
        "created": "2016-12-05T22:29:35Z",
        "minDisk": 20,
        "progress": 100,
        "minRam": 512,
        "metadata": {"architecture": "amd64"}
    },
    {
        "status": "ACTIVE",
        "updated": "2016-12-05T22:30:29Z",
        "id": get_id(),
        "OS-EXT-IMG-SIZE:size": 260899328,
        "name": name(),
        "created": "2016-12-05T22:29:35Z",
        "minDisk": 20,
        "progress": 100,
        "minRam": 512,
        "metadata": {"architecture": "amd64"}
    },
    {
        "status": "ACTIVE",
        "updated": "2016-12-05T22:30:29Z",
        "id": get_id(),
        "OS-EXT-IMG-SIZE:size": 260899328,
        "name": name(),
        "created": "2016-12-05T22:29:35Z",
        "minDisk": 20,
        "progress": 100,
        "minRam": 512,
        "metadata": {"architecture": "amd64"}
    },
    {
        "status": "ACTIVE",
        "updated": "2016-12-05T22:30:29Z",
        "id": get_id(),
        "OS-EXT-IMG-SIZE:size": 260899328,
        "name": name(),
        "created": "2016-12-05T22:29:35Z",
        "minDisk": 20,
        "progress": 100,
        "minRam": 512,
        "metadata": {"architecture": "amd64"}
    }
]


@route('/nova/v2.1/<project_id>/images/detail', method='GET')
@route('/nova/v2.1/<project_id>/images', method='GET')
def nova_images_details(project_id):
    resp = {"images": IMAGES}
    return resp


@route('/nova/v2.1/<project_id>/images/<image_id>', method='GET')
def nova_image_get(project_id, image_id):
    for image in IMAGES:
        if image['id'] == image_id:
            return {"image": image}


FLAVORS = [
  {
    "name": name(),
    "ram": 1024,
    "OS-FLV-DISABLED:disabled": False,
    "vcpus": 1,
    "swap": "",
    "os-flavor-access:is_public": True,
    "rxtx_factor": 1.0,
    "OS-FLV-EXT-DATA:ephemeral": 0,
    "disk": 20,
    "id": get_id()
  },
  {
    "name": name(),
    "ram": 2048,
    "OS-FLV-DISABLED:disabled": False,
    "vcpus": 1,
    "swap": "",
    "os-flavor-access:is_public": True,
    "rxtx_factor": 1.0,
    "OS-FLV-EXT-DATA:ephemeral": 0,
    "disk": 20,
    "id": get_id()
  },
  {
    "name": name(),
    "ram": 4096,
    "OS-FLV-DISABLED:disabled": False,
    "vcpus": 1,
    "swap": "",
    "os-flavor-access:is_public": True,
    "rxtx_factor": 1.0,
    "OS-FLV-EXT-DATA:ephemeral": 0,
    "disk": 20,
    "id": get_id()
  }
]


@route('/nova/v2.1/<project_id>/flavors/detail', method='GET')
@route('/nova/v2.1/<project_id>/flavors', method='GET')
def flavor_list_detail(project_id):
    resp = {"flavors": FLAVORS}
    return resp


@route('/nova/v2.1/<project_id>/flavors/<flavor_id>', method='GET')
def flavor_get(project_id, flavor_id):
    for flavor in FLAVORS:
        if flavor['id'] == flavor_id:
            return {"flavor": flavor}
    raise


@route('/neutron/v2.0/extensions.json', method='GET')
def network_extensions():
    return {
        "extensions": [
            {
                "updated": "2013-01-20T00:00:00-00:00",
                "name": "Neutron Service Type Management",
                "links": [],
                "alias": "service-type",
                "description": "API for retrieving service providers for Neutron advanced services"
            },
            {
                "updated": "2012-10-05T10:00:00-00:00",
                "name": "security-group",
                "links": [],
                "alias": "security-group",
                "description": "The security groups extension."
            }
        ]
    }


@route('/neutron/v2.0/networks.json', method='GET')
def network_list():
    return {
        "networks": [
            {
                "status": "ACTIVE",
                "subnets": [
                    "abc"
                ],
                "name": "private-network",
                "provider:physical_network": None,
                "admin_state_up": True,
                "project_id": "4fd44f30292945e481c7b8a0c8908869",
                "tenant_id": "4fd44f30292945e481c7b8a0c8908869",
                "qos_policy_id": "6a8454ade84346f59e8d40665f878b2e",
                "provider:network_type": "local",
                "router:external": True,
                "mtu": 0,
                "shared": True,
                "id": "d32019d3-bc6e-4319-9c1d-6722fc136a22",
                "provider:segmentation_id": None
            }
        ]
    }


@route('/neutron/v2.0/subnets.json', method='GET')
def subnet_list():
    print(request.headers.__dict__)
    return {
        "subnets": [
            {
                "name": "private-subnet",
                "enable_dhcp": True,
                "network_id": "db193ab3-96e3-4cb3-8fc5-05f4296d0324",
                "segment_id": None,
                "project_id": "26a7980765d0414dbc1fc1f88cdb7e6e",
                "tenant_id": "26a7980765d0414dbc1fc1f88cdb7e6e",
                "dns_nameservers": [],
                "allocation_pools": [
                    {
                        "start": get_ip(),
                        "end": get_ip()
                    }
                ],
                "host_routes": [],
                "ip_version": 4,
                "gateway_ip": get_ip(),
                "cidr": f"{get_ip()}/24",
                "id": "abc",
                "created_at": "2016-10-10T14:35:34Z",
                "description": "",
                "ipv6_address_mode": None,
                "ipv6_ra_mode": None,
                "revision_number": 2,
                "service_types": [],
                "subnetpool_id": None,
                "updated_at": "2016-10-10T14:35:34Z"
            }
        ]
    }


@route('/nova/v2.1/<project_id>/servers', method='POST')
def server_create(project_id):
    image_id = request.json['server']['imageRef']
    flavor_id = request.json['server']['flavorRef']
    name = request.json['server']['name']
    response.status = 202
    server_id = get_id()
    new_server = {"server": {
        "status": "ACTIVE",
        "updated": "2017-01-23T17:25:40Z",
        "hostId": "8e1376bbeee19c6fb07e29eb7876ac26ac81905200a10d3dfac6840c",
        "OS-EXT-SRV-ATTR:host": "saturn-rpc",
        "addresses": {
            "private-net": [{"OS-EXT-IPS-MAC:mac_addr": "fa:16:3e:58:ad:d4", "version": 4, "addr": get_ip(), "OS-EXT-IPS:type": "fixed"}],
            "external-net": [{"OS-EXT-IPS-MAC:mac_addr": "fa:16:3e:b0:a3:13", "version": 4, "addr": get_ip(), "OS-EXT-IPS:type": "fixed"}]},
        "key_name": None,
        "image": {
            "id": image_id
        },
        "OS-EXT-STS:task_state": None,
        "OS-EXT-STS:vm_state": "active",
        "OS-EXT-SRV-ATTR:instance_name": "instance-00000157",
        "OS-SRV-USG:launched_at": "2017-01-23T17:25:40.000000",
        "OS-EXT-SRV-ATTR:hypervisor_hostname": "saturn-rpc",
        "flavor": {"id": flavor_id},
        "id": server_id,
        "security_groups": [{"name": "default"}, {"name": "default"}],
        "OS-SRV-USG:terminated_at": None,
        "OS-EXT-AZ:availability_zone": "nova",
        "user_id": "c95c5f5773864aacb5c09498a4e4ad0c",
        "name": name,
        "created": "2017-01-23T17:25:27Z",
        "tenant_id": project_id,
        "OS-DCF:diskConfig": "MANUAL",
        "os-extended-volumes:volumes_attached": [],
        "accessIPv4": get_ip(),
        "accessIPv6": "",
        "progress": 0,
        "OS-EXT-STS:power_state": 1,
        "config_drive": "",
        "metadata": {}}
    }
    SERVERS[server_id] = new_server
    return new_server


@route('/nova/v2.1/<project_id>/servers/detail')
def server_list(project_id):
    resp = {"servers": []}
    for server in SERVERS.values():
        resp["servers"].append(server["server"])
    return resp


# Note: May also need /nova/v2.1/<project_id/servers?name=<server_name> someday
@route('/nova/v2.1/<project_id>/servers/<server_id>', method='GET')
def server_get(project_id, server_id):
    return SERVERS.get(server_id)


@route('/nova/v2.1/<project_id>/servers/<server_id>', method='DELETE')
def server_delete(project_id, server_id):
    response.status = 202
    del SERVERS[server_id]
    SERVER_IDS.insert(0, server_id)
    return


@route('/nova/v2.1/<project_id>/os-availability-zone')
def availability_zone(project_id):
    print(request.headers['X-Auth-Token'])
    return {
        "availabilityZoneInfo": [
            {
                "hosts": None,
                "zoneName": "nova",
                "zoneState": {
                    "available": True
                }
            }
        ]
    }


@route('/nova/v2.1/<project_id>/limits', method='GET')
def server_quota_get(project_id):
    return {
        'servers': {
            'used': len(SERVERS),
            'limit': 10
        }
    }


@route('/cinder/v2/<project_id>/types')
def cinder_types(project_id):
    return {
        "volume_types": [
            {
                "extra_specs": {
                    "capabilities": "gpu"
                },
                "id": "6685584b-1eac-4da6-b5c3-555430cf68ff",
                "name": "SSD"
            },
            {
                "extra_specs": {},
                "id": "8eb69a46-df97-4e41-9586-9a40a7533803",
                "name": "SATA"
            }
        ]
    }


@route('/')
def root():
    response.status = 300
    return {
      "versions": {
        "values": [
          {
            "status": "stable",
            "updated": "2016-04-04T00:00:00Z",
            "media-types": [
              {
                "base": "application/json",
                "type": "application/vnd.openstack.identity-v3+json"
              }
            ],
            "id": "v3.6",
            "links": [
              {
                "href": "http://{host}:{port}/v3/".format(host=HOST, port=PORT),
                "rel": "self"
              }
            ]
          },
          {
            "status": "stable",
            "updated": "2014-04-17T00:00:00Z",
            "media-types": [
              {
                "base": "application/json",
                "type": "application/vnd.openstack.identity-v2.0+json"
              }
            ],
            "id": "v2.0",
            "links": [
              {
                "href": "http://{host}:{port}/v2.0/".format(host=HOST, port=PORT),
                "rel": "self"
              },
              {
                "href": "http://docs.openstack.org/",
                "type": "text/html", "rel": "describedby"
              }
            ]
          }
        ]
      }
    }


LOG.info(f'starting mock openstack server on {PORT}')
run(host='0.0.0.0', port=PORT, debug=True, reloader=True)

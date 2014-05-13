# Copyright (C) 2014 Kristoffer Gronlund <kgronlund@suse.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
# unit tests for cliformat.py

import cibconfig
from lxml import etree
from test_parse import MockValidation
from nose.tools import eq_

factory = cibconfig.cib_factory


def assert_is_not_none(thing):
    if thing is None:
        message = "%s was None" % (thing)
        raise AssertionError(message)


def roundtrip(cli, debug=False):
    node, _, _ = cibconfig.parse_cli_to_xml(cli, validation=MockValidation())
    assert_is_not_none(node)
    obj = factory.create_from_node(node)
    assert_is_not_none(obj)
    obj.nocli = True
    xml = obj.repr_cli(format=-1)
    print xml
    obj.nocli = False
    s = obj.repr_cli(format=-1)
    if s != cli:
        print "GOT:", s
        print "EXP:", cli
    if debug:
        print s
        print cli
    assert obj.cli_use_validate()
    eq_(cli, s)
    assert not debug


def setup_func():
    "set up test fixtures"
    import idmgmt
    idmgmt.clear()


def teardown_func():
    "tear down test fixtures"


def test_rscset():
    roundtrip('colocation foo inf: a b')
    roundtrip('order order_2 Mandatory: [ A B ] C')
    roundtrip('rsc_template public_vm Xen')


def test_group():
    factory.create_from_cli('primitive p1 Dummy')
    roundtrip('group g1 p1 params target-role=Stopped')


def test_bnc863736():
    roundtrip('order order_3 Mandatory: [ A B ] C symmetrical=true')


def test_sequential():
    roundtrip('colocation rsc_colocation-master inf: [ vip-master vip-rep sequential="true" ] [ msPostgresql:Master sequential="true" ]')

def test_broken_colo():
    xml = """<rsc_colocation id="colo-2" score="INFINITY">
  <resource_set id="colo-2-0" require-all="false">
    <resource_ref id="vip1"/>
    <resource_ref id="vip2"/>
  </resource_set>
  <resource_set id="colo-2-1" require-all="false" role="Master">
    <resource_ref id="apache"/>
  </resource_set>
</rsc_colocation>"""
    data = etree.fromstring(xml)
    obj = factory.create_from_node(data)
    assert_is_not_none(obj)
    data = obj.repr_cli(format=-1)
    eq_('colocation colo-2 inf: [ vip1 vip2 sequential="true" ] [ apache:Master sequential="true" ]', data)
    assert obj.cli_use_validate()


def test_comment():
    roundtrip("# comment 1\nprimitive d0 ocf:pacemaker:Dummy")


def test_comment2():
    roundtrip("# comment 1\n# comment 2\n# comment 3\nprimitive d0 ocf:pacemaker:Dummy")


def test_ordering():
    xml = """<primitive id="dummy" class="ocf" provider="pacemaker" type="Dummy"> \
  <operations> \
    <op name="start" timeout="60" interval="0" id="dummy-start-0"/> \
    <op name="stop" timeout="60" interval="0" id="dummy-stop-0"/> \
    <op name="monitor" interval="60" timeout="30" id="dummy-monitor-60"/> \
  </operations> \
  <meta_attributes id="dummy-meta_attributes"> \
    <nvpair id="dummy-meta_attributes-target-role" name="target-role"
value="Stopped"/> \
  </meta_attributes> \
</primitive>"""
    data = etree.fromstring(xml)
    obj = factory.create_from_node(data)
    assert_is_not_none(obj)
    data = obj.repr_cli(format=-1)
    print data
    exp = 'primitive dummy ocf:pacemaker:Dummy op start timeout=60 interval=0 op stop timeout=60 interval=0 op monitor interval=60 timeout=30 meta target-role=Stopped'
    eq_(exp, data)
    assert obj.cli_use_validate()


def test_ordering2():
    xml = """<primitive id="dummy2" class="ocf" provider="pacemaker" type="Dummy"> \
  <meta_attributes id="dummy2-meta_attributes"> \
    <nvpair id="dummy2-meta_attributes-target-role" name="target-role"
value="Stopped"/> \
  </meta_attributes> \
  <operations> \
    <op name="start" timeout="60" interval="0" id="dummy2-start-0"/> \
    <op name="stop" timeout="60" interval="0" id="dummy2-stop-0"/> \
    <op name="monitor" interval="60" timeout="30" id="dummy2-monitor-60"/> \
  </operations> \
</primitive>"""
    data = etree.fromstring(xml)
    obj = factory.create_from_node(data)
    assert_is_not_none(obj)
    data = obj.repr_cli(format=-1)
    print data
    exp = 'primitive dummy2 ocf:pacemaker:Dummy meta target-role=Stopped op start timeout=60 interval=0 op stop timeout=60 interval=0 op monitor interval=60 timeout=30'
    eq_(exp, data)
    assert obj.cli_use_validate()

def test_fencing():
    xml = """<fencing-topology>
    <fencing-level devices="st1" id="fencing" index="1"
target="ha-three"></fencing-level>
    <fencing-level devices="st1" id="fencing-0" index="1"
target="ha-two"></fencing-level>
    <fencing-level devices="st1" id="fencing-1" index="1"
target="ha-one"></fencing-level>
  </fencing-topology>"""
    data = etree.fromstring(xml)
    obj = factory.create_from_node(data)
    assert_is_not_none(obj)
    data = obj.repr_cli(format=-1)
    print data
    exp = 'fencing_topology st1'
    eq_(exp, data)
    assert obj.cli_use_validate()


def test_master():
    xml = """<master id="ms-1">
    <crmsh-ref id="dummy3" />
    </master>
    """
    data = etree.fromstring(xml)
    factory.create_from_cli("primitive dummy3 ocf:pacemaker:Dummy")
    data, _, _ = cibconfig.postprocess_cli(data)
    print "after postprocess:", etree.tostring(data)
    obj = factory.create_from_node(data)
    assert_is_not_none(obj)
    assert obj.cli_use_validate()


def test_param_rules():
    roundtrip('primitive foo Dummy ' +
              'params rule #uname eq wizbang laser=yes ' +
              'params rule #uname eq gandalf staff=yes')

    roundtrip('primitive mySpecialRsc me:Special ' +
              'params 3: rule #uname eq node1 interface=eth1 ' +
              'params 2: rule #uname eq node2 interface=eth2 port=8888 ' +
              'params 1: interface=eth0 port=9999')

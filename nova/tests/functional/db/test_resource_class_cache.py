#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import datetime
import mock

from oslo_utils import timeutils

from nova.db.sqlalchemy import resource_class_cache as rc_cache
from nova import exception
from nova import rc_fields as fields
from nova import test
from nova.tests import fixtures


class TestResourceClassCache(test.TestCase):

    def setUp(self):
        super(TestResourceClassCache, self).setUp()
        self.db = self.useFixture(fixtures.Database(database='api'))
        self.context = mock.Mock()
        sess_mock = mock.Mock()
        sess_mock.connection.side_effect = self.db.get_engine().connect
        self.context.session = sess_mock

    @mock.patch('sqlalchemy.select')
    def test_rc_cache_std_no_db(self, sel_mock):
        """Test that looking up either an ID or a string in the resource class
        cache for a standardized resource class does not result in a DB
        call.
        """
        cache = rc_cache.ResourceClassCache(self.context)

        self.assertEqual('VCPU', cache.string_from_id(0))
        self.assertEqual('MEMORY_MB', cache.string_from_id(1))
        self.assertEqual(0, cache.id_from_string('VCPU'))
        self.assertEqual(1, cache.id_from_string('MEMORY_MB'))

        self.assertFalse(sel_mock.called)

    def test_standards(self):
        cache = rc_cache.ResourceClassCache(self.context)
        standards = cache.STANDARDS

        self.assertEqual(len(standards), len(fields.ResourceClass.STANDARD))
        names = (rc['name'] for rc in standards)
        for name in fields.ResourceClass.STANDARD:
            self.assertIn(name, names)

        cache = rc_cache.ResourceClassCache(self.context)
        standards2 = cache.STANDARDS
        self.assertEqual(id(standards), id(standards2))

    def test_standards_have_time_fields(self):
        cache = rc_cache.ResourceClassCache(self.context)
        standards = cache.STANDARDS

        first_standard = standards[0]
        self.assertIn('updated_at', first_standard)
        self.assertIn('created_at', first_standard)
        self.assertIsNone(first_standard['updated_at'])
        self.assertIsNone(first_standard['created_at'])

    def test_standard_has_time_fields(self):
        cache = rc_cache.ResourceClassCache(self.context)

        vcpu_class = cache.all_from_string('VCPU')
        expected = {'id': 0, 'name': 'VCPU', 'updated_at': None,
                    'created_at': None}
        self.assertEqual(expected, vcpu_class)

    def test_rc_cache_custom(self):
        """Test that non-standard, custom resource classes hit the database and
        return appropriate results, caching the results after a single
        query.
        """
        cache = rc_cache.ResourceClassCache(self.context)

        # Haven't added anything to the DB yet, so should raise
        # ResourceClassNotFound
        self.assertRaises(exception.ResourceClassNotFound,
                          cache.string_from_id, 1001)
        self.assertRaises(exception.ResourceClassNotFound,
                          cache.id_from_string, "IRON_NFV")

        # Now add to the database and verify appropriate results...
        with self.context.session.connection() as conn:
            ins_stmt = rc_cache._RC_TBL.insert().values(
                id=1001,
                name='IRON_NFV'
            )
            conn.execute(ins_stmt)

        self.assertEqual('IRON_NFV', cache.string_from_id(1001))
        self.assertEqual(1001, cache.id_from_string('IRON_NFV'))

        # Try same again and verify we don't hit the DB.
        with mock.patch('sqlalchemy.select') as sel_mock:
            self.assertEqual('IRON_NFV', cache.string_from_id(1001))
            self.assertEqual(1001, cache.id_from_string('IRON_NFV'))
            self.assertFalse(sel_mock.called)

        # Verify all fields available from all_from_string
        iron_nfv_class = cache.all_from_string('IRON_NFV')
        self.assertEqual(1001, iron_nfv_class['id'])
        self.assertEqual('IRON_NFV', iron_nfv_class['name'])
        # updated_at not set on insert
        self.assertIsNone(iron_nfv_class['updated_at'])
        self.assertIsInstance(iron_nfv_class['created_at'], datetime.datetime)

        # Update IRON_NFV (this is a no-op but will set updated_at)
        with self.context.session.connection() as conn:
            # NOTE(cdent): When using explict SQL that names columns,
            # the automatic timestamp handling provided by the oslo_db
            # TimestampMixin is not provided. created_at is a default
            # but updated_at is an onupdate.
            upd_stmt = rc_cache._RC_TBL.update().where(
                rc_cache._RC_TBL.c.id == 1001).values(
                    name='IRON_NFV', updated_at=timeutils.utcnow())
            conn.execute(upd_stmt)

        # reset cache
        cache = rc_cache.ResourceClassCache(self.context)

        iron_nfv_class = cache.all_from_string('IRON_NFV')
        # updated_at set on update
        self.assertIsInstance(iron_nfv_class['updated_at'], datetime.datetime)

    def test_rc_cache_miss(self):
        """Test that we raise ResourceClassNotFound if an unknown resource
        class ID or string is searched for.
        """
        cache = rc_cache.ResourceClassCache(self.context)
        self.assertRaises(exception.ResourceClassNotFound,
                          cache.string_from_id, 99999999)
        self.assertRaises(exception.ResourceClassNotFound,
                          cache.id_from_string, 'UNKNOWN')

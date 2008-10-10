# -*- coding: utf-8 -*-
#
# test_import.py - Tests for the lobbyists module import_* functions.
# Copyright (C) 2008 by Drew Hess <dhess@bothan.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/>.

"""Tests for the lobbyists module import_* functions."""

import unittest
import lobbyists
import sqlite3
import util

def filing_values(parsed_filings):
    """Iterate over filing dictionaries in a sequence of parsed filings."""
    for x in parsed_filings:
        yield x['filing']


class TestImport(unittest.TestCase):
    def test_preloaded_table_state_or_local_gov(self):
        """Is the state_or_local_gov table preloaded by the schema file?"""
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT val FROM state_or_local_gov")
        rows = set([row[0] for row in cur])
        self.failUnlessEqual(len(rows), 3)
        self.failUnless('unspecified' in rows)
        self.failUnless('y' in rows)
        self.failUnless('n' in rows)
        
    def test_preloaded_table_client_status(self):
        """Is the client_status table preloaded by the schema file?"""
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT status FROM client_status")
        rows = set([row[0] for row in cur])
        self.failUnlessEqual(len(rows), 3)
        self.failUnless('active' in rows)
        self.failUnless('terminated' in rows)
        self.failUnless('administratively terminated' in rows)
        
    def test_preloaded_table_lobbyist_status(self):
        """Is the lobbyist_status table preloaded by the schema file?"""
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT status FROM lobbyist_status")
        rows = set([row[0] for row in cur])
        self.failUnlessEqual(len(rows), 3)
        self.failUnless('active' in rows)
        self.failUnless('terminated' in rows)
        self.failUnless('undetermined' in rows)
        
    def test_preloaded_table_lobbyist_indicator(self):
        """Is the lobbyist_indicator table preloaded by the schema file?"""
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT status FROM lobbyist_indicator")
        rows = set([row[0] for row in cur])
        self.failUnlessEqual(len(rows), 3)
        self.failUnless('covered' in rows)
        self.failUnless('not covered' in rows)
        self.failUnless('undetermined' in rows)
        
    def test_import_filings(self):
        filings = [x for x in lobbyists.parse_filings(util.testpath('filings.xml'))]
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))

        # Read back, sort and compare
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM filing")
        rows = [row for row in cur]
        rows.sort(key=lambda x: x['id'])
        filings.sort(key=lambda x: x['filing']['id'])

        self.failUnlessEqual(len(rows), len(filings))
        for (row, filing) in zip(rows, filing_values(filings)):
            self.failUnlessEqual(row['id'], filing['id'])
            self.failUnlessEqual(row['type'], filing['type'])
            self.failUnlessEqual(row['year'], filing['year'])
            self.failUnlessEqual(row['period'], filing['period'])
            self.failUnlessEqual(row['filing_date'], filing['filing_date'])
            self.failUnlessEqual(row['amount'], filing['amount'])
            # All of these filings have no Registrant, no Client.
            self.failUnless(row['registrant'] is None)
            self.failUnless(row['client'] is None)
        
    def test_import_filings_to_registrants(self):
        """Ensure filing rows point to the correct registrants."""
        filings = [x for x in lobbyists.parse_filings(util.testpath('registrants.xml'))]
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))

        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT filing.id AS filing_id, \
                            registrant.address AS address, \
                            registrant.description AS description, \
                            registrant.country AS country, \
                            registrant.senate_id AS senate_id, \
                            registrant.name AS name, \
                            registrant.ppb_country AS ppb_country \
                     FROM filing INNER JOIN registrant ON \
                            registrant.id=filing.registrant")
        rows = [row for row in cur]
        rows.sort(key=lambda x: x['filing_id'])
        registrants = [x for x in filings if 'registrant' in x]
        registrants.sort(key=lambda x: x['filing']['id'])
        self.failUnlessEqual(len(rows), len(registrants))
        for (row, filing) in zip(rows, registrants):
            self.failUnlessEqual(row['filing_id'], filing['filing']['id'])
            reg = filing['registrant']
            self.failUnlessEqual(row['address'], reg['address'])
            self.failUnlessEqual(row['description'], reg['description'])
            self.failUnlessEqual(row['country'], reg['country'])
            self.failUnlessEqual(row['senate_id'], reg['senate_id'])
            self.failUnlessEqual(row['name'], reg['name'])
            self.failUnlessEqual(row['ppb_country'], reg['ppb_country'])

    def test_import_registrant_countries(self):
        """Ensure importing registrants fills the 'country' table."""
        filings = [x for x in lobbyists.parse_filings(util.testpath('registrants.xml'))]
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))

        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM country")
        rows = [row['name'] for row in cur]
        registrants = [x for x in filings if 'registrant' in x]
        countries = set([x['registrant']['country'] for x in registrants])
        countries = countries.union([x['registrant']['ppb_country'] for x in \
                                         registrants])
        self.failUnlessEqual(len(rows), len(countries))
        for country in countries:
            self.failUnless(country in rows)
        
    def test_import_registrant_orgs(self):
        """Ensure importing registrants fills the 'org' table."""
        filings = [x for x in lobbyists.parse_filings(util.testpath('registrants.xml'))]
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))

        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM org")
        rows = [row['name'] for row in cur]
        registrants = [x for x in filings if 'registrant' in x]
        orgs = set([x['registrant']['name'] for x in registrants])
        self.failUnlessEqual(len(rows), len(orgs))
        for org in orgs:
            self.failUnless(org in rows)
        
    def dup_test(self, file, column, table):
        filings = [x for x in lobbyists.parse_filings(util.testpath(file))]
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))
        cur = con.cursor()
        cur.execute('SELECT %s FROM %s' % (column, table))
        row1, row2 = cur.fetchall()
        return row1, row2

    def test_import_identical_registrants(self):
        """Identical registrants shouldn't be duplicated in the database"""
        filings = [x for x in lobbyists.parse_filings(util.testpath('registrants_dup.xml'))]
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))
        cur = con.cursor()
        cur.execute('SELECT filing.registrant \
                      FROM filing')
        row1, row2 = cur.fetchall()
        self.failUnlessEqual(row1[0], row2[0])

    def test_import_similar_registrants(self):
        """Ensure slightly different registrants are inserted into different rows."""
        filings = [x for x in lobbyists.parse_filings(util.testpath('registrants_slightly_different.xml'))]
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))
        cur = con.cursor()
        cur.execute('SELECT filing.registrant \
                      FROM filing')
        self.failUnlessEqual(len(cur.fetchall()), len(filings))

    def test_import_filings_to_clients(self):
        """Ensure filing rows point to the correct clients."""
        filings = [x for x in lobbyists.parse_filings(util.testpath('clients.xml'))]
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))
                  
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT filing.id AS filing_id, \
                            client.country AS country, \
                            client.senate_id as senate_id, \
                            client.name as name, \
                            client.ppb_country as ppb_country, \
                            client.state as state, \
                            client.ppb_state as ppb_state, \
                            client.status as status, \
                            client.description as description, \
                            client.state_or_local_gov as state_or_local_gov, \
                            client.contact_name as contact_name \
                     FROM filing INNER JOIN client ON \
                            client.id=filing.client")
        rows = [row for row in cur]
        rows.sort(key=lambda x: x['filing_id'])
        clients = [x for x in filings if 'client' in x]
        clients.sort(key=lambda x: x['filing']['id'])
        self.failUnlessEqual(len(rows), len(clients))
        for (row, filing) in zip(rows, clients):
            self.failUnlessEqual(row['filing_id'], filing['filing']['id'])
            client = filing['client']
            self.failUnlessEqual(row['country'], client['country'])
            self.failUnlessEqual(row['senate_id'], client['senate_id'])
            self.failUnlessEqual(row['name'], client['name'])
            self.failUnlessEqual(row['ppb_country'], client['ppb_country'])
            self.failUnlessEqual(row['state'], client['state'])
            self.failUnlessEqual(row['ppb_state'], client['ppb_state'])
            self.failUnlessEqual(row['status'], client['status'])
            self.failUnlessEqual(row['description'], client['description'])
            self.failUnlessEqual(row['state_or_local_gov'], client['state_or_local_gov'])
            self.failUnlessEqual(row['contact_name'], client['contact_name'])

    def test_import_identical_clients(self):
        """Identical clients shouldn't be duplicated in the database."""
        row1, row2 = self.dup_test('clients_dup.xml', 'client', 'filing')
        self.failUnlessEqual(row1[0], row2[0])

    def test_import_similar_clients(self):
        """Ensure slightly different clients are inserted into different rows."""
        filings = [x for x in lobbyists.parse_filings(\
                util.testpath('clients_slightly_different.xml'))]
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))
        cur = con.cursor()
        cur.execute('SELECT id FROM client')
        clients = [x['client'] for x in filings if 'client' in x]
        self.failUnlessEqual(len(cur.fetchall()), len(clients))

    def test_import_client_orgs(self):
        """Importing clients should fill the 'org' table."""
        filings = [x for x in lobbyists.parse_filings(util.testpath('clients.xml'))]
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))

        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM org")
        rows = [row['name'] for row in cur]
        clients = [x for x in filings if 'client' in x]
        orgs = set([x['client']['name'] for x in clients])
        self.failUnlessEqual(len(rows), len(orgs))
        for org in orgs:
            self.failUnless(org in rows)
        
    def test_import_client_countries(self):
        """Importing clients should fill the 'country' table."""
        filings = [x for x in lobbyists.parse_filings(util.testpath('clients.xml'))]
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))

        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM country")
        rows = [row['name'] for row in cur]
        clients = [x for x in filings if 'client' in x]
        countries = set([x['client']['country'] for x in clients])
        countries = countries.union([x['client']['ppb_country'] for x in \
                                         clients])
        self.failUnlessEqual(len(rows), len(countries))
        for country in countries:
            self.failUnless(country in rows)
        

    def test_import_client_states(self):
        """Importing clients should fill the 'state' table."""
        filings = [x for x in lobbyists.parse_filings(util.testpath('clients.xml'))]
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))

        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM state")
        rows = [row['name'] for row in cur]
        clients = [x for x in filings if 'client' in x]
        states = set([x['client']['state'] for x in clients])
        states = states.union([x['client']['ppb_state'] for x in \
                                         clients])
        self.failUnlessEqual(len(rows), len(states))
        for state in states:
            self.failUnless(state in rows)
        
    def test_import_client_persons(self):
        """Importing clients should fill the 'person' table."""
        filings = [x for x in lobbyists.parse_filings(util.testpath('clients.xml'))]
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))

        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM person")
        rows = [row['name'] for row in cur]
        clients = [x for x in filings if 'client' in x]
        persons = set([x['client']['contact_name'] for x in clients])
        self.failUnlessEqual(len(rows), len(persons))
        for person in persons:
            self.failUnless(person in rows)
        
    def test_import_client_state_or_local_gov(self):
        """After importing clients, state_or_local_gov table should be unchanged (it's pre-loaded)."""
        filings = [x for x in lobbyists.parse_filings(util.testpath('clients.xml'))]
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT val FROM state_or_local_gov")
        rows = set([row[0] for row in cur])
        self.failUnlessEqual(len(rows), 3)
        self.failUnless('unspecified' in rows)
        self.failUnless('y' in rows)
        self.failUnless('n' in rows)
        
    def test_import_client_client_status(self):
        """After importing clients, client_status table should be unchanged (it's pre-loaded)."""
        filings = [x for x in lobbyists.parse_filings(util.testpath('clients.xml'))]
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT status FROM client_status")
        rows = set([row[0] for row in cur])
        self.failUnlessEqual(len(rows), 3)
        self.failUnless('active' in rows)
        self.failUnless('terminated' in rows)
        self.failUnless('administratively terminated' in rows)

    def test_import_lobbyists(self):
        """Check lobbyist importing."""
        filings = [x for x in lobbyists.parse_filings(util.testpath('lobbyists.xml'))]
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))

        # Some of the other import tests just compare the parsed
        # filings to the contents of the database, but for various
        # reasons that's difficult for lobbyist records.  Instead,
        # this test has knowledge of the contents of the
        # 'lobbyists.xml' test file, and checks the database contents
        # explicitly, ala the parser tests in test_parser.py.
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM lobbyist")
        rows = [row for row in cur]

        row = rows.pop()
        self.failUnlessEqual(row['id'], 16)
        self.failUnlessEqual(row['name'], 'KNUTSON, KENT')
        self.failUnlessEqual(row['status'], 'active')
        self.failUnlessEqual(row['indicator'], 'undetermined')
        self.failUnlessEqual(row['official_position'], 'N/A')
        
        row = rows.pop()
        self.failUnlessEqual(row['id'], 15)
        self.failUnlessEqual(row['name'], 'KNUTSON, KENT')
        self.failUnlessEqual(row['status'], 'active')
        self.failUnlessEqual(row['indicator'], 'not covered')
        self.failUnlessEqual(row['official_position'], 'N/A')
        
        row = rows.pop()
        self.failUnlessEqual(row['id'], 14)
        self.failUnlessEqual(row['name'], 'CHAMPLIN, STEVEN')
        self.failUnlessEqual(row['status'], 'active')
        self.failUnlessEqual(row['indicator'], 'not covered')
        self.failUnlessEqual(row['official_position'], 'ExecFlrAsst, H. Maj. Whip; ExecDir, H.DemCauc.')
        
        row = rows.pop()
        self.failUnlessEqual(row['id'], 13)
        self.failUnlessEqual(row['name'], 'GRIFFIN, BRIAN')
        self.failUnlessEqual(row['status'], 'active')
        self.failUnlessEqual(row['indicator'], 'not covered')
        self.failUnlessEqual(row['official_position'], 'StaffAsst, DemPolicyComm; FlrAsst, MinoritySec')
        
        row = rows.pop()
        self.failUnlessEqual(row['id'], 12)
        self.failUnlessEqual(row['name'], 'DUBERSTEIN, KENNETH')
        self.failUnlessEqual(row['status'], 'active')
        self.failUnlessEqual(row['indicator'], 'not covered')
        self.failUnlessEqual(row['official_position'], 'Chief of Staff, President Reagan')
        
        row = rows.pop()
        self.failUnlessEqual(row['id'], 11)
        self.failUnlessEqual(row['name'], 'UELAND, ERIC')
        self.failUnlessEqual(row['status'], 'active')
        self.failUnlessEqual(row['indicator'], 'not covered')
        self.failUnlessEqual(row['official_position'], 'AsstEditor/Ed./Res.Dir, Sen.Rep.PolicyComm;')
        
        row = rows.pop()
        self.failUnlessEqual(row['id'], 10)
        self.failUnlessEqual(row['name'], 'BEDWELL, EDWARD T')
        self.failUnlessEqual(row['status'], 'terminated')
        self.failUnlessEqual(row['indicator'], 'undetermined')
        self.failUnlessEqual(row['official_position'], 'unspecified')
        
        row = rows.pop()
        self.failUnlessEqual(row['id'], 9)
        self.failUnlessEqual(row['name'], 'LEHMAN (MY 2006), PATRICK')
        self.failUnlessEqual(row['status'], 'terminated')
        self.failUnlessEqual(row['indicator'], 'undetermined')
        self.failUnlessEqual(row['official_position'], 'unspecified')
        
        row = rows.pop()
        self.failUnlessEqual(row['id'], 8)
        self.failUnlessEqual(row['name'], 'NEAL, KATIE')
        self.failUnlessEqual(row['status'], 'active')
        self.failUnlessEqual(row['indicator'], 'covered')
        self.failUnlessEqual(row['official_position'], 'COMM DIR/REP DINGELL')
        
        row = rows.pop()
        self.failUnlessEqual(row['id'], 7)
        self.failUnlessEqual(row['name'], 'NEAL, KATIE')
        self.failUnlessEqual(row['status'], 'active')
        self.failUnlessEqual(row['indicator'], 'not covered')
        self.failUnlessEqual(row['official_position'], 'N/A')
        
        row = rows.pop()
        self.failUnlessEqual(row['id'], 6)
        self.failUnlessEqual(row['name'], 'NEAL, KATIE')
        self.failUnlessEqual(row['status'], 'active')
        self.failUnlessEqual(row['indicator'], 'undetermined')
        self.failUnlessEqual(row['official_position'], 'unspecified')
        
        row = rows.pop()
        self.failUnlessEqual(row['id'], 5)
        self.failUnlessEqual(row['name'], 'unspecified')
        self.failUnlessEqual(row['status'], 'terminated')
        self.failUnlessEqual(row['indicator'], 'not covered')
        self.failUnlessEqual(row['official_position'], 'unspecified')
        
        row = rows.pop()
        self.failUnlessEqual(row['id'], 4)
        self.failUnlessEqual(row['name'], 'MCKENNEY, WILLIAM')
        self.failUnlessEqual(row['status'], 'active')
        self.failUnlessEqual(row['indicator'], 'not covered')
        self.failUnlessEqual(row['official_position'], 'Staff Director, Ways & Means Over Sub')
        
        row = rows.pop()
        self.failUnlessEqual(row['id'], 3)
        self.failUnlessEqual(row['name'], 'DENNIS, JAMES')
        self.failUnlessEqual(row['status'], 'active')
        self.failUnlessEqual(row['indicator'], 'not covered')
        self.failUnlessEqual(row['official_position'], 'Tax Counsel, Sen Robb - Counsel, Sen Bingaman')
        
        row = rows.pop()
        self.failUnlessEqual(row['id'], 2)
        self.failUnlessEqual(row['name'], 'GRAFMEYER, RICHARD')
        self.failUnlessEqual(row['status'], 'active')
        self.failUnlessEqual(row['indicator'], 'not covered')
        self.failUnlessEqual(row['official_position'], 'Deputy Chief of Staff, JCT')
        
        row = rows.pop()
        self.failUnlessEqual(row['id'], 1)
        self.failUnlessEqual(row['name'], 'HARRIS, ROBERT L.')
        self.failUnlessEqual(row['status'], 'undetermined')
        self.failUnlessEqual(row['indicator'], 'undetermined')
        self.failUnlessEqual(row['official_position'], 'unspecified')
        
        self.failUnlessEqual(len(rows), 0)

    def test_import_filings_to_lobbyists(self):
        """Ensure lobbyists are matched up with filings in the database."""
        filings = [x for x in lobbyists.parse_filings(util.testpath('lobbyists.xml'))]
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))

        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM filing_lobbyists")
        rows = [row for row in cur]

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '771F3B6A-315D-4190-88F3-2CE0F138B2B8')
        self.failUnlessEqual(row['lobbyist'], 16)
        
        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '771F3B6A-315D-4190-88F3-2CE0F138B2B8')
        self.failUnlessEqual(row['lobbyist'], 15)
        
        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             'BD894C51-AA23-46AE-9802-006B8C91702B')
        self.failUnlessEqual(row['lobbyist'], 14)
        
        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             'BD894C51-AA23-46AE-9802-006B8C91702B')
        self.failUnlessEqual(row['lobbyist'], 13)
        
        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             'BD894C51-AA23-46AE-9802-006B8C91702B')
        self.failUnlessEqual(row['lobbyist'], 12)
        
        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             'BD894C51-AA23-46AE-9802-006B8C91702B')
        self.failUnlessEqual(row['lobbyist'], 11)
        
        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '2164D6BB-EBBA-40D2-9C18-16A2D670030A')
        self.failUnlessEqual(row['lobbyist'], 10)
        
        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '87A30FA6-7C35-4294-BA43-4CE7B5B808B3')
        self.failUnlessEqual(row['lobbyist'], 9)
        
        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '0FC23296-F948-43FD-98D4-0912F6579E6A')
        self.failUnlessEqual(row['lobbyist'], 8)
        
        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '0FC23296-F948-43FD-98D4-0912F6579E6A')
        self.failUnlessEqual(row['lobbyist'], 7)
        
        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '0FC23296-F948-43FD-98D4-0912F6579E6A')
        self.failUnlessEqual(row['lobbyist'], 6)
        
        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '02DDA99B-725A-4DBA-8397-34892A6918D7')
        self.failUnlessEqual(row['lobbyist'], 5)
        
        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '02DDA99B-725A-4DBA-8397-34892A6918D7')
        self.failUnlessEqual(row['lobbyist'], 4)
        
        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '02DDA99B-725A-4DBA-8397-34892A6918D7')
        self.failUnlessEqual(row['lobbyist'], 3)
        
        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '02DDA99B-725A-4DBA-8397-34892A6918D7')
        self.failUnlessEqual(row['lobbyist'], 2)
        
        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '04926911-8A12-4A0E-9DA4-510869446EAC')
        self.failUnlessEqual(row['lobbyist'], 1)
        
    def test_import_lobbyist_person(self):
        """Importing lobbyists should fill the 'person' table."""
        filings = [x for x in lobbyists.parse_filings(util.testpath('lobbyists.xml'))]
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))

        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM person")
        rows = [row['name'] for row in cur]
        lobbyers = util.flatten([x['lobbyists'] for x in filings if 'lobbyists' in x])
        names = set([x['lobbyist']['name'] for x in lobbyers])
        self.failUnlessEqual(len(rows), len(names))
        for name in names:
            self.failUnless(name in rows)

    def test_import_lobbyist_lobbyist_status(self):
        """After import, lobbyist_status table should be unchanged (it's pre-loaded)."""
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT status FROM lobbyist_status")
        rows = set([row[0] for row in cur])
        self.failUnlessEqual(len(rows), 3)
        self.failUnless('active' in rows)
        self.failUnless('terminated' in rows)
        self.failUnless('undetermined' in rows)
        
    def test_import_lobbyist_lobbyist_indicator(self):
        """After import, lobbyist_indicator table should be unchanged (it's pre-loaded)."""
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT status FROM lobbyist_indicator")
        rows = set([row[0] for row in cur])
        self.failUnlessEqual(len(rows), 3)
        self.failUnless('covered' in rows)
        self.failUnless('not covered' in rows)
        self.failUnless('undetermined' in rows)
        
    def test_import_identical_lobbyists(self):
        """Identical lobbyists shouldn't be duplicated in the database."""
        row1, row2 = self.dup_test('lobbyists_dup.xml', 'lobbyist', 'filing_lobbyists')
        self.failUnlessEqual(row1[0], row2[0])

    def test_import_identical_lobbyists2(self):
        """Identical lobbyists shouldn't be duplicated in the database (case 2)."""
        # This test file contains a single filing with two
        # lobbyists. The two lobbyists are exactly the same. This
        # should result in only a single entry in the filing_lobbyists
        # table.
        filings = [x for x in lobbyists.parse_filings(util.testpath('lobbyists_dup2.xml'))]
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))
        cur = con.cursor()
        cur.execute('SELECT lobbyist FROM filing_lobbyists')
        rows = cur.fetchall()
        self.failUnlessEqual(len(rows), 1)

    def test_import_similar_lobbyists(self):
        """Ensure slightly different lobbyists are inserted into different rows."""
        filings = [x for x in lobbyists.parse_filings(\
                util.testpath('lobbyists_slightly_different.xml'))]
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))
        cur = con.cursor()
        cur.execute('SELECT id FROM lobbyist')
        lobbyers = util.flatten([x['lobbyists'] for x in filings if 'lobbyists' in x])
        self.failUnlessEqual(len(cur.fetchall()), len(lobbyers))

    def test_import_govt_entities(self):
        """Check government entity importing."""
        filings = [x for x in lobbyists.parse_filings(util.testpath('govt_entities.xml'))]
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))

        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM govt_entity")
        rows = [row for row in cur]

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'UNDETERMINED')
        
        row = rows.pop()
        self.failUnlessEqual(row['name'],
                             'Federal Communications Commission (FCC)')
        
        row = rows.pop()
        self.failUnlessEqual(row['name'],
                             'Environmental Protection Agency (EPA)')
        
        row = rows.pop()
        self.failUnlessEqual(row['name'], 'Energy, Dept of')
        
        row = rows.pop()
        self.failUnlessEqual(row['name'],
                             'Federal Energy Regulatory Commission (FERC)')
        
        row = rows.pop()
        self.failUnlessEqual(row['name'],
                             'Health & Human Services, Dept of  (HHS)')
        
        row = rows.pop()
        self.failUnlessEqual(row['name'], 'SENATE')
        
        row = rows.pop()
        self.failUnlessEqual(row['name'], 'HOUSE OF REPRESENTATIVES')
        
        row = rows.pop()
        self.failUnlessEqual(row['name'], 'NONE')
        
        self.failUnlessEqual(len(rows), 0)

    def test_import_filings_to_govt_entities(self):
        """Ensure government entities are matched up with filings in the database."""
        filings = [x for x in lobbyists.parse_filings(util.testpath('govt_entities.xml'))]
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))

        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM filing_govt_entities")
        rows = [row for row in cur]

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '2627E811-33AB-43F4-B8E0-5B979A10FBF9')
        self.failUnlessEqual(row['govt_entity'], 'UNDETERMINED')
        
        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '106C2C6E-F0E1-46E3-9409-294E0BD27878')
        self.failUnlessEqual(row['govt_entity'],
                             'Federal Communications Commission (FCC)')
        
        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '106C2C6E-F0E1-46E3-9409-294E0BD27878')
        self.failUnlessEqual(row['govt_entity'],
                             'Environmental Protection Agency (EPA)')
        
        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '106C2C6E-F0E1-46E3-9409-294E0BD27878')
        self.failUnlessEqual(row['govt_entity'],'Energy, Dept of')
        
        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '106C2C6E-F0E1-46E3-9409-294E0BD27878')
        self.failUnlessEqual(row['govt_entity'],
                             'HOUSE OF REPRESENTATIVES')        
        
        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '106C2C6E-F0E1-46E3-9409-294E0BD27878')
        self.failUnlessEqual(row['govt_entity'],
                             'Federal Energy Regulatory Commission (FERC)')
        
        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '106C2C6E-F0E1-46E3-9409-294E0BD27878')
        self.failUnlessEqual(row['govt_entity'], 'SENATE')
        
        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             'FFF29969-FDEC-4125-809E-0D8D2D8E73FC')
        self.failUnlessEqual(row['govt_entity'],
                             'Health & Human Services, Dept of  (HHS)')

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             'FFF29969-FDEC-4125-809E-0D8D2D8E73FC')
        self.failUnlessEqual(row['govt_entity'], 'SENATE')
        
        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             'FFF29969-FDEC-4125-809E-0D8D2D8E73FC')
        self.failUnlessEqual(row['govt_entity'],
                             'HOUSE OF REPRESENTATIVES')        
        
        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             'FD29F4AF-763B-42A6-A27E-0AE115CD6D51')
        self.failUnlessEqual(row['govt_entity'], 'NONE')
        
        self.failUnlessEqual(len(rows), 0)
        
    def test_import_issues(self):
        """Check issues importing."""
        filings = list(lobbyists.parse_filings(util.testpath('issues.xml')))
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))

        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM issue")
        rows = list(cur)

        row = rows.pop()
        self.failUnlessEqual(row['id'], 23)
        self.failUnlessEqual(row['code'],
                             'ENERGY/NUCLEAR')
        self.failUnlessEqual(row['specific_issue'],
                             '\r\nComprehensive Energy Bill')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 22)
        self.failUnlessEqual(row['code'],
                             'TRANSPORTATION')
        self.failUnlessEqual(row['specific_issue'],
                             '\r\nH.R. 1495 Water Resources Development Act (WRDA) - the WRDA provisions to modernize the locks on the Upper Mississippi and Illinois Rivers are essential if U.S. agriculture is going to remain competitive in the global marketplace.\r\nH.R. 1495 the Water Resources Development Act of 2007 (WRDA) - conference report - Title VIII of the legislation includes authorization for the Corps of Engineers to construct new 1,200 foot locks on the Upper Mississippi and Illinois Rivers\n')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 21)
        self.failUnlessEqual(row['code'],
                             'IMMIGRATION')
        self.failUnlessEqual(row['specific_issue'],
                             '\r\nImmigration - Thanking Senator Lincoln and her staff for the hard work and long hours and dedication they presented in an effort to develop a comprehensive immigration reform.\n')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 20)
        self.failUnlessEqual(row['code'],
                             'AGRICULTURE')
        self.failUnlessEqual(row['specific_issue'],
                             '\r\nFY08 Agriculture Appropriations Bill - (Sec. 738) amendment to prohibit USDA from spending money for health inspection of horses.\n\nH.R. 3161, the FY08 Ag spending bill - amendments: King/Kingston amendment to strike Sec. 738. It would limit USDA authority for equine health inspection, effectively restricting the movement of all horses; Ackerman amendment prohibits funding for Food Safety and Inspection Service (FSIS) inspections in facilities that process nonambulatory or downer livestock;  Whitfield-Spratt-Rahall-Chandler amendment to restrict USDA inspection of horses intended for processing for human consumption.\n\nPayment Limits.\r\nFarm Bill: tax title, reductions in direct payments, counter-cyclical revenue option, senate ag committee markup on farm bill, amendments seeking further reform to payment limits and adjusted gross income restrictions.\n')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 19)
        self.failUnlessEqual(row['code'],
                             'TRADE (DOMESTIC/FOREIGN)')
        self.failUnlessEqual(row['specific_issue'],
                             '\r\nU.S. -Peru Trade Promotion Agreement (TPA) - the goal is to increase U.S. agriculture exports and increase market share.')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 18)
        self.failUnlessEqual(row['code'],
                             'EDUCATION')
        self.failUnlessEqual(row['specific_issue'],
                             '\r\nFY08 Labor, HHS and Education spending.  Perkins Amendment (federal funding for FFA and career and technical education).')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 17)
        self.failUnlessEqual(row['code'],
                             'ROADS/HIGHWAY')
        self.failUnlessEqual(row['specific_issue'],
                             '\r\nH.R. 3098 to restore farm truck exemptions from federal motor carrier vehicle regulations.')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 16)
        self.failUnlessEqual(row['code'],
                             'DEFENSE')
        self.failUnlessEqual(row['specific_issue'],
                             'H.R.3222 & Senate FY08 Defense Appropriations-Navy, Army & SOCOM R&D\nH.R.1585 & S.1547 FY08 Defense Authorizations-Navy, Army & SOCOM R&D\n')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 15)
        self.failUnlessEqual(row['code'],
                             'HOMELAND SECURITY')
        self.failUnlessEqual(row['specific_issue'],
                             'H.R.3222 & Senate FY08 Defense Appropriations-Navy, Army & SOCOM R&D\nH.R.1585 & S.1547 FY08 Defense Authorizations-Navy, Army & SOCOM R&D\nH.R.2638 & S.1644 FY08 DHS AppropriationsBill-CRP')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 14)
        self.failUnlessEqual(row['code'],
                             'BUDGET/APPROPRIATIONS')
        self.failUnlessEqual(row['specific_issue'],
                             'H.R.3222 & Senate FY08 Defense Appropriations-Navy, Army & SOCOM R&D\nH.R.1585 & S.1547 FY08 Defense Authorizations-Navy, Army & SOCOM R&D\nH.R.2638 & S.1644 FY08 DHS AppropriationsBill-CRP')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 13)
        self.failUnlessEqual(row['code'],
                             'DEFENSE')
        self.failUnlessEqual(row['specific_issue'],
                             'DEFENSE AUTHORIZATION, DEFENSE APPROPRIATIONS, VETERANS, DEFENSE HEALTH CARE, ARMED FORCES RETIREMENT, ARMED FORCES PERSONNEL BENEFITS, EMERGING DEFENSE RELATED ISSUES')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 12)
        self.failUnlessEqual(row['code'],
                             'BANKING')
        self.failUnlessEqual(row['specific_issue'],
                             'unspecified')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 11)
        self.failUnlessEqual(row['code'],
                             'REAL ESTATE/LAND USE/CONSERVATION')
        self.failUnlessEqual(row['specific_issue'],
                             'unspecified')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 10)
        self.failUnlessEqual(row['code'],
                             'FINANCIAL INSTITUTIONS/INVESTMENTS/SECURITIES')
        self.failUnlessEqual(row['specific_issue'],
                             'unspecified')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 9)
        self.failUnlessEqual(row['code'],
                             'FOREIGN RELATIONS')
        self.failUnlessEqual(row['specific_issue'],
                             'unspecified')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 8)
        self.failUnlessEqual(row['code'],
                             'LAW ENFORCEMENT/CRIME/CRIMINAL JUSTICE')
        self.failUnlessEqual(row['specific_issue'],
                             'unspecified')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 7)
        self.failUnlessEqual(row['code'],
                             'FAMILY ISSUES/ABORTION/ADOPTION')
        self.failUnlessEqual(row['specific_issue'],
                             'unspecified')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 6)
        self.failUnlessEqual(row['code'],
                             'HEALTH ISSUES')
        self.failUnlessEqual(row['specific_issue'],
                             'unspecified')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 5)
        self.failUnlessEqual(row['code'],
                             'MEDICARE/MEDICAID')
        self.failUnlessEqual(row['specific_issue'],
                             'unspecified')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 4)
        self.failUnlessEqual(row['code'],
                             'WELFARE')
        self.failUnlessEqual(row['specific_issue'],
                             'unspecified')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 3)
        self.failUnlessEqual(row['code'],
                             'BUDGET/APPROPRIATIONS')
        self.failUnlessEqual(row['specific_issue'],
                             'unspecified')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 2)
        self.failUnlessEqual(row['code'],
                             'TAXATION/INTERNAL REVENUE CODE')
        self.failUnlessEqual(row['specific_issue'],
                             'unspecified')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 1)
        self.failUnlessEqual(row['code'],
                             'INSURANCE')
        self.failUnlessEqual(row['specific_issue'],
                             'unspecified')

        self.failUnlessEqual(len(rows), 0)

    def test_import_issues_issue_code(self):
        """Importing issues should fill issue_code table."""
        filings = list(lobbyists.parse_filings(util.testpath('issues.xml')))
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))

        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM issue_code")
        rows = list(cur)

        row = rows.pop()
        self.failUnlessEqual(row['code'],
                             'ENERGY/NUCLEAR')

        row = rows.pop()
        self.failUnlessEqual(row['code'],
                             'TRANSPORTATION')

        row = rows.pop()
        self.failUnlessEqual(row['code'],
                             'IMMIGRATION')

        row = rows.pop()
        self.failUnlessEqual(row['code'],
                             'AGRICULTURE')

        row = rows.pop()
        self.failUnlessEqual(row['code'],
                             'TRADE (DOMESTIC/FOREIGN)')

        row = rows.pop()
        self.failUnlessEqual(row['code'],
                             'EDUCATION')

        row = rows.pop()
        self.failUnlessEqual(row['code'],
                             'ROADS/HIGHWAY')

        row = rows.pop()
        self.failUnlessEqual(row['code'],
                             'HOMELAND SECURITY')

        row = rows.pop()
        self.failUnlessEqual(row['code'],
                             'DEFENSE')

        row = rows.pop()
        self.failUnlessEqual(row['code'],
                             'BANKING')

        row = rows.pop()
        self.failUnlessEqual(row['code'],
                             'REAL ESTATE/LAND USE/CONSERVATION')

        row = rows.pop()
        self.failUnlessEqual(row['code'],
                             'FINANCIAL INSTITUTIONS/INVESTMENTS/SECURITIES')

        row = rows.pop()
        self.failUnlessEqual(row['code'],
                             'FOREIGN RELATIONS')

        row = rows.pop()
        self.failUnlessEqual(row['code'],
                             'LAW ENFORCEMENT/CRIME/CRIMINAL JUSTICE')

        row = rows.pop()
        self.failUnlessEqual(row['code'],
                             'FAMILY ISSUES/ABORTION/ADOPTION')

        row = rows.pop()
        self.failUnlessEqual(row['code'],
                             'HEALTH ISSUES')

        row = rows.pop()
        self.failUnlessEqual(row['code'],
                             'MEDICARE/MEDICAID')

        row = rows.pop()
        self.failUnlessEqual(row['code'],
                             'WELFARE')

        row = rows.pop()
        self.failUnlessEqual(row['code'],
                             'BUDGET/APPROPRIATIONS')

        row = rows.pop()
        self.failUnlessEqual(row['code'],
                             'TAXATION/INTERNAL REVENUE CODE')

        row = rows.pop()
        self.failUnlessEqual(row['code'],
                             'INSURANCE')

        self.failUnlessEqual(len(rows), 0)

    def test_import_filings_to_issues(self):
        """Ensure issues are matched up with filings in the database."""
        filings = list(lobbyists.parse_filings(util.testpath('issues.xml')))
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))

        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM filing_issues")
        rows = list(cur)

        row = rows.pop()
        self.failUnlessEqual(row['filing'], '79E53F91-8C5F-44AD-909D-032AA25D5B00')
        self.failUnlessEqual(row['issue'], 23)

        row = rows.pop()
        self.failUnlessEqual(row['filing'], '79E53F91-8C5F-44AD-909D-032AA25D5B00')
        self.failUnlessEqual(row['issue'], 22)

        row = rows.pop()
        self.failUnlessEqual(row['filing'], '79E53F91-8C5F-44AD-909D-032AA25D5B00')
        self.failUnlessEqual(row['issue'], 21)

        row = rows.pop()
        self.failUnlessEqual(row['filing'], '79E53F91-8C5F-44AD-909D-032AA25D5B00')
        self.failUnlessEqual(row['issue'], 20)

        row = rows.pop()
        self.failUnlessEqual(row['filing'], '79E53F91-8C5F-44AD-909D-032AA25D5B00')
        self.failUnlessEqual(row['issue'], 19)

        row = rows.pop()
        self.failUnlessEqual(row['filing'], '79E53F91-8C5F-44AD-909D-032AA25D5B00')
        self.failUnlessEqual(row['issue'], 18)

        row = rows.pop()
        self.failUnlessEqual(row['filing'], '79E53F91-8C5F-44AD-909D-032AA25D5B00')
        self.failUnlessEqual(row['issue'], 17)

        row = rows.pop()
        self.failUnlessEqual(row['filing'], '05804BE5-57C9-41BF-97B2-0120826D4393')
        self.failUnlessEqual(row['issue'], 16)

        row = rows.pop()
        self.failUnlessEqual(row['filing'], '05804BE5-57C9-41BF-97B2-0120826D4393')
        self.failUnlessEqual(row['issue'], 15)

        row = rows.pop()
        self.failUnlessEqual(row['filing'], '05804BE5-57C9-41BF-97B2-0120826D4393')
        self.failUnlessEqual(row['issue'], 14)

        row = rows.pop()
        self.failUnlessEqual(row['filing'], 'F56492FC-4FBD-4824-83E1-0004B30F0519')
        self.failUnlessEqual(row['issue'], 13)

        row = rows.pop()
        self.failUnlessEqual(row['filing'], 'A55002C7-78C4-41BA-A6CA-01FCF7650116')
        self.failUnlessEqual(row['issue'], 12)

        row = rows.pop()
        self.failUnlessEqual(row['filing'], 'A55002C7-78C4-41BA-A6CA-01FCF7650116')
        self.failUnlessEqual(row['issue'], 11)

        row = rows.pop()
        self.failUnlessEqual(row['filing'], 'A55002C7-78C4-41BA-A6CA-01FCF7650116')
        self.failUnlessEqual(row['issue'], 10)

        row = rows.pop()
        self.failUnlessEqual(row['filing'], 'A55002C7-78C4-41BA-A6CA-01FCF7650116')
        self.failUnlessEqual(row['issue'], 9)

        row = rows.pop()
        self.failUnlessEqual(row['filing'], 'A55002C7-78C4-41BA-A6CA-01FCF7650116')
        self.failUnlessEqual(row['issue'], 8)

        row = rows.pop()
        self.failUnlessEqual(row['filing'], 'A55002C7-78C4-41BA-A6CA-01FCF7650116')
        self.failUnlessEqual(row['issue'], 7)

        row = rows.pop()
        self.failUnlessEqual(row['filing'], 'D1C9DB2A-AE4F-4FED-9BCB-024C8373813E')
        self.failUnlessEqual(row['issue'], 6)

        row = rows.pop()
        self.failUnlessEqual(row['filing'], 'D1C9DB2A-AE4F-4FED-9BCB-024C8373813E')
        self.failUnlessEqual(row['issue'], 5)

        row = rows.pop()
        self.failUnlessEqual(row['filing'], 'D1C9DB2A-AE4F-4FED-9BCB-024C8373813E')
        self.failUnlessEqual(row['issue'], 4)

        row = rows.pop()
        self.failUnlessEqual(row['filing'], 'D1C9DB2A-AE4F-4FED-9BCB-024C8373813E')
        self.failUnlessEqual(row['issue'], 3)

        row = rows.pop()
        self.failUnlessEqual(row['filing'], 'D1C9DB2A-AE4F-4FED-9BCB-024C8373813E')
        self.failUnlessEqual(row['issue'], 2)

        row = rows.pop()
        self.failUnlessEqual(row['filing'], 'D1C9DB2A-AE4F-4FED-9BCB-024C8373813E')
        self.failUnlessEqual(row['issue'], 1)

        self.failUnlessEqual(len(rows), 0)

    def test_import_affiliated_orgs(self):
        """Check affiliated org importing."""
        filings = list(lobbyists.parse_filings(util.testpath('affiliated_orgs.xml')))
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))

        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM affiliated_org")
        rows = [row for row in cur]

        row = rows.pop()
        self.failUnlessEqual(row['id'], 31)
        self.failUnlessEqual(row['name'], 'PORTAL DEL FUTURO AUTHORITY')
        self.failUnlessEqual(row['country'], 'PUERTO RICO')
        self.failUnlessEqual(row['ppb_country'], 'PUERTO RICO')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 30)
        self.failUnlessEqual(row['name'], 'ITNL EMISSIONS TRADING ASSN')
        self.failUnlessEqual(row['country'], 'unspecified')
        self.failUnlessEqual(row['ppb_country'], 'UNDETERMINED')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 29)
        self.failUnlessEqual(row['name'], 'ISL')
        self.failUnlessEqual(row['country'], 'UNDETERMINED')
        self.failUnlessEqual(row['ppb_country'], 'USA')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 28)
        self.failUnlessEqual(row['name'], 'CHILDRENS HOSPITAL OAKLAND')
        self.failUnlessEqual(row['country'], 'USA')
        self.failUnlessEqual(row['ppb_country'], 'USA')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 27)
        self.failUnlessEqual(row['name'], 'INMARSAT LTD')
        self.failUnlessEqual(row['country'], 'UNITED KINGDOM')
        self.failUnlessEqual(row['ppb_country'], 'UNDETERMINED')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 26)
        self.failUnlessEqual(row['name'], 'UC GROUP LIMITED')
        self.failUnlessEqual(row['country'], 'UNITED KINGDOM')
        self.failUnlessEqual(row['ppb_country'], 'USA')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 25)
        self.failUnlessEqual(row['name'], 'N/A')
        self.failUnlessEqual(row['country'], 'USA')
        self.failUnlessEqual(row['ppb_country'], 'UNDETERMINED')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 24)
        self.failUnlessEqual(row['name'], 'Time Warner Cable')
        self.failUnlessEqual(row['country'], 'USA')
        self.failUnlessEqual(row['ppb_country'], 'USA')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 23)
        self.failUnlessEqual(row['name'], 'Palm, Inc.')
        self.failUnlessEqual(row['country'], '<SELECT ONE>')
        self.failUnlessEqual(row['ppb_country'], '<SELECT ONE>')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 22)
        self.failUnlessEqual(row['name'], 'Warner Bros.')
        self.failUnlessEqual(row['country'], 'USA')
        self.failUnlessEqual(row['ppb_country'], 'USA')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 21)
        self.failUnlessEqual(row['name'], 'AOL')
        self.failUnlessEqual(row['country'], 'USA')
        self.failUnlessEqual(row['ppb_country'], 'USA')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 20)
        self.failUnlessEqual(row['name'], 'Power Pyles Sutter & Verville')
        self.failUnlessEqual(row['country'], 'USA')
        self.failUnlessEqual(row['ppb_country'], 'USA')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 19)
        self.failUnlessEqual(row['name'], 'Holland and Knight')
        self.failUnlessEqual(row['country'], 'USA')
        self.failUnlessEqual(row['ppb_country'], 'USA')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 18)
        self.failUnlessEqual(row['name'], 'HCR ManorCare')
        self.failUnlessEqual(row['country'], 'USA')
        self.failUnlessEqual(row['ppb_country'], 'USA')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 17)
        self.failUnlessEqual(row['name'], 'Vitas')
        self.failUnlessEqual(row['country'], 'USA')
        self.failUnlessEqual(row['ppb_country'], 'USA')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 16)
        self.failUnlessEqual(row['name'], 'Odyssey')
        self.failUnlessEqual(row['country'], 'USA')
        self.failUnlessEqual(row['ppb_country'], 'USA')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 15)
        self.failUnlessEqual(row['name'], 'AseraCare')
        self.failUnlessEqual(row['country'], 'USA')
        self.failUnlessEqual(row['ppb_country'], 'USA')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 14)
        self.failUnlessEqual(row['name'], 'UT-Battelle')
        self.failUnlessEqual(row['country'], 'USA')
        self.failUnlessEqual(row['ppb_country'], 'USA')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 13)
        self.failUnlessEqual(row['name'], 'Brookhaven Science Association')
        self.failUnlessEqual(row['country'], 'USA')
        self.failUnlessEqual(row['ppb_country'], 'USA')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 12)
        self.failUnlessEqual(row['name'], 'Ross Stores, Inc.')
        self.failUnlessEqual(row['country'], 'USA')
        self.failUnlessEqual(row['ppb_country'], 'USA')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 11)
        self.failUnlessEqual(row['name'], 'Wal-Mart Stores, Inc.')
        self.failUnlessEqual(row['country'], 'USA')
        self.failUnlessEqual(row['ppb_country'], 'USA')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 10)
        self.failUnlessEqual(row['name'], "Land O'Lakes, Inc.")
        self.failUnlessEqual(row['country'], 'USA')
        self.failUnlessEqual(row['ppb_country'], 'USA')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 9)
        self.failUnlessEqual(row['name'], 'SOUTHEASTERN FEDERAL POWER CUSTOME')
        self.failUnlessEqual(row['country'], 'USA')
        self.failUnlessEqual(row['ppb_country'], 'USA')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 8)
        self.failUnlessEqual(row['name'], 'Patton Boggs, LLP')
        self.failUnlessEqual(row['country'], 'USA')
        self.failUnlessEqual(row['ppb_country'], 'USA')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 7)
        self.failUnlessEqual(row['name'], 'CARITAS CHRISTI')
        self.failUnlessEqual(row['country'], 'USA')
        self.failUnlessEqual(row['ppb_country'], 'USA')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 6)
        self.failUnlessEqual(row['name'], 'BOSTON MEDICAL CENTER')
        self.failUnlessEqual(row['country'], 'USA')
        self.failUnlessEqual(row['ppb_country'], 'USA')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 5)
        self.failUnlessEqual(row['name'], 'PARTNERS HEALTHCARE SYSTEM')
        self.failUnlessEqual(row['country'], 'USA')
        self.failUnlessEqual(row['ppb_country'], 'USA')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 4)
        self.failUnlessEqual(row['name'], 'DANA FARBER CANCER INSTITUTE')
        self.failUnlessEqual(row['country'], 'USA')
        self.failUnlessEqual(row['ppb_country'], 'USA')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 3)
        self.failUnlessEqual(row['name'], 'ORANGE COUNTY TRANSPORTATION AUTHOR')
        self.failUnlessEqual(row['country'], 'USA')
        self.failUnlessEqual(row['ppb_country'], 'USA')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 2)
        self.failUnlessEqual(row['name'], 'JERRY REDDEN')
        self.failUnlessEqual(row['country'], 'USA')
        self.failUnlessEqual(row['ppb_country'], 'USA')

        row = rows.pop()
        self.failUnlessEqual(row['id'], 1)
        self.failUnlessEqual(row['name'], 'EXXONMOBILE')
        self.failUnlessEqual(row['country'], 'USA')
        self.failUnlessEqual(row['ppb_country'], 'USA')

        self.failUnlessEqual(len(rows), 0)

    def test_import_filings_to_affiliated_orgs(self):
        """Ensure affiliated orgs are matched up with filings in the database."""
        filings = list(lobbyists.parse_filings(util.testpath('affiliated_orgs.xml')))
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))

        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM filing_affiliated_orgs")
        rows = [row for row in cur]

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             'F0054303-E42F-48CE-8D71-CE7B2FBE8707')
        self.failUnlessEqual(row['org'], 31)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             'A4F6A122-5550-46AF-9C5C-2838FF6538FE')
        self.failUnlessEqual(row['org'], 30)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             'A0AA1F41-447E-4A0B-B09A-B0C24645F805')
        self.failUnlessEqual(row['org'], 29)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             'A0AA1F41-447E-4A0B-B09A-B0C24645F805')
        self.failUnlessEqual(row['org'], 28)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             'E63105D4-9840-492D-A81E-F6816CBAFACE')
        self.failUnlessEqual(row['org'], 27)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '9B506978-9D51-431A-A698-11F682485512')
        self.failUnlessEqual(row['org'], 26)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             'E8A4D9C9-2D0B-4F0A-966D-A076858D2751')
        self.failUnlessEqual(row['org'], 25)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '493C9C11-17ED-4875-88D2-FAC96FF06849')
        self.failUnlessEqual(row['org'], 24)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '493C9C11-17ED-4875-88D2-FAC96FF06849')
        self.failUnlessEqual(row['org'], 23)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '493C9C11-17ED-4875-88D2-FAC96FF06849')
        self.failUnlessEqual(row['org'], 22)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '493C9C11-17ED-4875-88D2-FAC96FF06849')
        self.failUnlessEqual(row['org'], 21)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '9B5A4E46-8AAA-4497-B11A-B83B6D18836C')
        self.failUnlessEqual(row['org'], 20)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '9B5A4E46-8AAA-4497-B11A-B83B6D18836C')
        self.failUnlessEqual(row['org'], 19)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '5F456254-75FE-4ED2-8F74-92C169B6800A')
        self.failUnlessEqual(row['org'], 18)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '5F456254-75FE-4ED2-8F74-92C169B6800A')
        self.failUnlessEqual(row['org'], 17)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '5F456254-75FE-4ED2-8F74-92C169B6800A')
        self.failUnlessEqual(row['org'], 16)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '5F456254-75FE-4ED2-8F74-92C169B6800A')
        self.failUnlessEqual(row['org'], 15)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             'C6EABAE0-1E89-491F-97B3-5282386EC69C')
        self.failUnlessEqual(row['org'], 14)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             'C6EABAE0-1E89-491F-97B3-5282386EC69C')
        self.failUnlessEqual(row['org'], 13)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '8A3DB5DF-04A3-4002-9353-2C12104A0B49')
        self.failUnlessEqual(row['org'], 12)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '8A3DB5DF-04A3-4002-9353-2C12104A0B49')
        self.failUnlessEqual(row['org'], 11)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '6D4AFEE6-E886-4993-B153-14A887FD325A')
        self.failUnlessEqual(row['org'], 10)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             'E34132EF-DA6D-40BF-BDEA-D13DBDF09BEA')
        self.failUnlessEqual(row['org'], 9)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '0C4051F5-2E0A-4ABC-A140-7FAFF7669D00')
        self.failUnlessEqual(row['org'], 8)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             'C8293344-9A8D-4D6F-AAA5-25925E60BED9')
        self.failUnlessEqual(row['org'], 7)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             'C8293344-9A8D-4D6F-AAA5-25925E60BED9')
        self.failUnlessEqual(row['org'], 6)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             'C8293344-9A8D-4D6F-AAA5-25925E60BED9')
        self.failUnlessEqual(row['org'], 5)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             'C8293344-9A8D-4D6F-AAA5-25925E60BED9')
        self.failUnlessEqual(row['org'], 4)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             'C72D65BA-24D0-4AB7-97E4-7D68FD2BCB7D')
        self.failUnlessEqual(row['org'], 3)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '09C471E9-2B98-433A-8E4D-0C3928459C20')
        self.failUnlessEqual(row['org'], 2)

        row = rows.pop()
        self.failUnlessEqual(row['filing'],
                             '16E1EA9C-F6B3-4319-957E-14F4D65BD9F4')
        self.failUnlessEqual(row['org'], 1)

        self.failUnlessEqual(len(rows), 0)
        
    def test_import_affiliated_org_to_urls(self):
        """Ensure affiliated orgs are matched up with URLs in the database."""
        filings = list(lobbyists.parse_filings(util.testpath('affiliated_orgs.xml')))
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))

        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM affiliated_org_urls")
        rows = [row for row in cur]

        row = rows.pop()
        self.failUnlessEqual(row['org'], 31)
        self.failUnlessEqual(row['url'],
                             'unspecified')

        row = rows.pop()
        self.failUnlessEqual(row['org'], 30)
        self.failUnlessEqual(row['url'],
                             'unspecified')

        row = rows.pop()
        self.failUnlessEqual(row['org'], 29)
        self.failUnlessEqual(row['url'],
                             'unspecified')

        row = rows.pop()
        self.failUnlessEqual(row['org'], 28)
        self.failUnlessEqual(row['url'],
                             'unspecified')

        row = rows.pop()
        self.failUnlessEqual(row['org'], 27)
        self.failUnlessEqual(row['url'],
                             'unspecified')

        row = rows.pop()
        self.failUnlessEqual(row['org'], 26)
        self.failUnlessEqual(row['url'],
                             'unspecified')

        row = rows.pop()
        self.failUnlessEqual(row['org'], 25)
        self.failUnlessEqual(row['url'],
                             'unspecified')

        row = rows.pop()
        self.failUnlessEqual(row['org'], 24)
        self.failUnlessEqual(row['url'],
                             "are the members listed on coalition's website?")

        row = rows.pop()
        self.failUnlessEqual(row['org'], 23)
        self.failUnlessEqual(row['url'],
                             "are the members listed on coalition's website?")

        row = rows.pop()
        self.failUnlessEqual(row['org'], 22)
        self.failUnlessEqual(row['url'],
                             "are the members listed on coalition's website?")

        row = rows.pop()
        self.failUnlessEqual(row['org'], 21)
        self.failUnlessEqual(row['url'],
                             "are the members listed on coalition's website?")

        row = rows.pop()
        self.failUnlessEqual(row['org'], 20)
        self.failUnlessEqual(row['url'],
                             'www.hklaw.com    www.ppsv.com')

        row = rows.pop()
        self.failUnlessEqual(row['org'], 19)
        self.failUnlessEqual(row['url'],
                             'www.hklaw.com    www.ppsv.com')

        row = rows.pop()
        self.failUnlessEqual(row['org'], 18)
        self.failUnlessEqual(row['url'],
                             'www.vitas.com, www.odyssey-healthcare.com, www.hcr-manorcare.com/home, www.aseracare.com')

        row = rows.pop()
        self.failUnlessEqual(row['org'], 17)
        self.failUnlessEqual(row['url'],
                             'www.vitas.com, www.odyssey-healthcare.com, www.hcr-manorcare.com/home, www.aseracare.com')

        row = rows.pop()
        self.failUnlessEqual(row['org'], 16)
        self.failUnlessEqual(row['url'],
                             'www.vitas.com, www.odyssey-healthcare.com, www.hcr-manorcare.com/home, www.aseracare.com')

        row = rows.pop()
        self.failUnlessEqual(row['org'], 15)
        self.failUnlessEqual(row['url'],
                             'www.vitas.com, www.odyssey-healthcare.com, www.hcr-manorcare.com/home, www.aseracare.com')

        row = rows.pop()
        self.failUnlessEqual(row['org'], 14)
        self.failUnlessEqual(row['url'],
                             'www.bnl.gov (Brookhaven Science Association);   www.ut-battelle.org (UT-Battelle)')

        row = rows.pop()
        self.failUnlessEqual(row['org'], 13)
        self.failUnlessEqual(row['url'],
                             'www.bnl.gov (Brookhaven Science Association);   www.ut-battelle.org (UT-Battelle)')

        row = rows.pop()
        self.failUnlessEqual(row['org'], 12)
        self.failUnlessEqual(row['url'],
                             'www.wal-mart.com; www.rossstores.com')

        row = rows.pop()
        self.failUnlessEqual(row['org'], 11)
        self.failUnlessEqual(row['url'],
                             'www.wal-mart.com; www.rossstores.com')
        
        row = rows.pop()
        self.failUnlessEqual(row['org'], 10)
        self.failUnlessEqual(row['url'],
                             'www.landolakesinc.com              4001 Lexington Ave. N, Arden Hills Minnesota 55112-6943')
        
        row = rows.pop()
        self.failUnlessEqual(row['org'], 9)
        self.failUnlessEqual(row['url'], 'None')
        
        row = rows.pop()
        self.failUnlessEqual(row['org'], 8)
        self.failUnlessEqual(row['url'],
                             'Patton Boggs, LLP, 2550 M. Street N.W., Washington, D.C. 20037 - pfarthing@pattonboggs.com')
        
        row = rows.pop()
        self.failUnlessEqual(row['org'], 7)
        self.failUnlessEqual(row['url'], 'N/A')
        
        row = rows.pop()
        self.failUnlessEqual(row['org'], 6)
        self.failUnlessEqual(row['url'], 'N/A')
        
        row = rows.pop()
        self.failUnlessEqual(row['org'], 5)
        self.failUnlessEqual(row['url'], 'N/A')
        
        row = rows.pop()
        self.failUnlessEqual(row['org'], 4)
        self.failUnlessEqual(row['url'], 'N/A')
        
        row = rows.pop()
        self.failUnlessEqual(row['org'], 3)
        self.failUnlessEqual(row['url'],  'judith_burrell@cox.net')
        
        row = rows.pop()
        self.failUnlessEqual(row['org'], 2)
        self.failUnlessEqual(row['url'],
                             'http://skipjack.net/le_shore/worcestr/welcome.html')
        
        row = rows.pop()
        self.failUnlessEqual(row['org'], 1)
        self.failUnlessEqual(row['url'], 'www.exxonmobile.com')
        
        self.failUnlessEqual(len(rows), 0)

    def test_import_affiliated_orgs_org(self):
        """Importing affiliated orgs should fill the 'org' table."""
        filings = list(lobbyists.parse_filings(util.testpath('affiliated_orgs.xml')))
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))

        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM org")
        rows = [row for row in cur]

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'PORTAL DEL FUTURO AUTHORITY')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'ITNL EMISSIONS TRADING ASSN')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'ISL')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'CHILDRENS HOSPITAL OAKLAND')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'INMARSAT LTD')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'UC GROUP LIMITED')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'N/A')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'Time Warner Cable')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'Palm, Inc.')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'Warner Bros.')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'AOL')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'Power Pyles Sutter & Verville')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'Holland and Knight')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'HCR ManorCare')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'Vitas')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'Odyssey')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'AseraCare')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'UT-Battelle')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'Brookhaven Science Association')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'Ross Stores, Inc.')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'Wal-Mart Stores, Inc.')

        row = rows.pop()
        self.failUnlessEqual(row['name'], "Land O'Lakes, Inc.")

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'SOUTHEASTERN FEDERAL POWER CUSTOME')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'Patton Boggs, LLP')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'CARITAS CHRISTI')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'BOSTON MEDICAL CENTER')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'PARTNERS HEALTHCARE SYSTEM')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'DANA FARBER CANCER INSTITUTE')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'ORANGE COUNTY TRANSPORTATION AUTHOR')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'JERRY REDDEN')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'EXXONMOBILE')

        self.failUnlessEqual(len(rows), 0)

    def test_import_affiliated_orgs_country(self):
        """Importing affiliated orgs should fill the 'country' table."""
        filings = list(lobbyists.parse_filings(util.testpath('affiliated_orgs.xml')))
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))

        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM country")
        rows = [row for row in cur]

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'PUERTO RICO')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'unspecified')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'UNITED KINGDOM')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'UNDETERMINED')

        row = rows.pop()
        self.failUnlessEqual(row['name'], '<SELECT ONE>')

        row = rows.pop()
        self.failUnlessEqual(row['name'], 'USA')

        self.failUnlessEqual(len(rows), 0)

    def test_import_affiliated_org_urls(self):
        """Importing affiliated orgs should fill the 'url' table."""
        filings = list(lobbyists.parse_filings(util.testpath('affiliated_orgs.xml')))
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))

        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM url")
        rows = [row for row in cur]

        row = rows.pop()
        self.failUnlessEqual(row['url'],
                             'unspecified')

        row = rows.pop()
        self.failUnlessEqual(row['url'],
                             "are the members listed on coalition's website?")

        row = rows.pop()
        self.failUnlessEqual(row['url'],
                             'www.hklaw.com    www.ppsv.com')

        row = rows.pop()
        self.failUnlessEqual(row['url'],
                             'www.vitas.com, www.odyssey-healthcare.com, www.hcr-manorcare.com/home, www.aseracare.com')

        row = rows.pop()
        self.failUnlessEqual(row['url'],
                             'www.bnl.gov (Brookhaven Science Association);   www.ut-battelle.org (UT-Battelle)')

        row = rows.pop()
        self.failUnlessEqual(row['url'],
                             'www.wal-mart.com; www.rossstores.com')

        row = rows.pop()
        self.failUnlessEqual(row['url'],
                             'www.landolakesinc.com              4001 Lexington Ave. N, Arden Hills Minnesota 55112-6943')
        
        row = rows.pop()
        self.failUnlessEqual(row['url'], 'None')
        
        row = rows.pop()
        self.failUnlessEqual(row['url'],
                             'Patton Boggs, LLP, 2550 M. Street N.W., Washington, D.C. 20037 - pfarthing@pattonboggs.com')
        
        row = rows.pop()
        self.failUnlessEqual(row['url'], 'N/A')
        
        row = rows.pop()
        self.failUnlessEqual(row['url'],  'judith_burrell@cox.net')
        
        row = rows.pop()
        self.failUnlessEqual(row['url'],
                             'http://skipjack.net/le_shore/worcestr/welcome.html')
        
        row = rows.pop()
        self.failUnlessEqual(row['url'], 'www.exxonmobile.com')
        
        self.failUnlessEqual(len(rows), 0)

    def test_import_identical_affiliated_orgs(self):
        """Identical affiliated orgs shouldn't be duplicated in the database."""
        row1, row2 = self.dup_test('affiliated_orgs_dup.xml',
                                   'org',
                                   'filing_affiliated_orgs')
        self.failUnlessEqual(row1[0], row2[0])

    def test_import_similar_affiliated_orgs(self):
        """Ensure slightly different affiliated orgs are inserted into different rows."""
        filings = list(lobbyists.parse_filings(util.testpath('affiliated_orgs_slightly_different.xml')))
        con = sqlite3.connect(':memory:')
        con = lobbyists.create_db(con)
        cur = con.cursor()
        self.failUnless(lobbyists.import_filings(cur, filings))
        cur = con.cursor()
        cur.execute('SELECT id FROM affiliated_org')
        orgs = util.flatten([x['affiliated_orgs'] for x in filings if 'affiliated_orgs' in x])
        self.failUnlessEqual(len(cur.fetchall()), len(orgs))


if __name__ == '__main__':
    unittest.main()
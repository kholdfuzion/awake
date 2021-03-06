# This file is part of Awake - GB decompiler.
# Copyright (C) 2012  Wojciech Marczenko (devdri) <wojtek.marczenko@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from urlparse import urlparse, parse_qs
import address
import flow
import tag
import operand
import jumptable
import procedure
import graph
from awake import database

def proc_page(addr, out):

    print 'proc page', str(addr)

    info = database.procInfo(addr)
    out.write('callers: ' + ', '.join(operand.ProcAddress(x).html() for x in info.callers) + '<br />')

    flow.refresh(addr)
    #out += 'deps: ' + str(flow.getProcDepSet(addr)) + '<br />'
    #out += 'calls: ' + ', '.join(operand.ProcAddress(x).html() for x in flow.at(addr).calls()) + '<br />'



    out.write(flow.at(addr).html())

    out.write(procedure.loadProcedureRange(addr).html())

def data_page(addr):
    print 'data page', str(addr)
    out = ''

    reads, writes = database.getDataReferers(addr)

    out += '<pre>\n'
    out += 'reads:\n'
    for x in reads:
        out += operand.ProcAddress(x).html() + '\n'
    out += 'writes:\n'
    for x in writes:
        out += operand.ProcAddress(x).html() + '\n'
    out += '</pre>\n'
    return out

def jumptable_page(addr):
    return jumptable.JumpTable(addr).html()

def name_form(addr):
    out = ''
    out += '<form class="name-form" method="get" action="/set-name">'
    out += '<input type="hidden" name="addr" value="{0}" />'.format(addr)
    out += '<input type="text" name="name" value="{0}" />'.format(tag.nameForAddress(addr))
    out += '<input type="submit" value="ok" />'
    out += '</form>'
    return out

class Handler(BaseHTTPRequestHandler):

    def redirect(self, where):
        self.send_response(301)
        self.send_header('Location', where)
        self.end_headers()

    def ok_html(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html;charset=utf-8')
        self.end_headers()

    def do_GET(self):

        print 'get', self.path

        if self.path.startswith('/proc/'):

            p = self.path.split('/')

            self.ok_html()
            self.wfile.write("<html><head><link rel=\"stylesheet\" type=\"text/css\" href=\"/style.css\" /></head><body>")
            addr = address.fromConventional(p[2])
            self.wfile.write(name_form(addr))
            proc_page(addr, self.wfile)
            self.wfile.write("</body></html>")

        elif self.path.startswith('/home'):

            self.ok_html()
            self.wfile.write("<html><head><link rel=\"stylesheet\" type=\"text/css\" href=\"/style.css\" /></head><body>")
            self.wfile.write(database.getInteresting())
            self.wfile.write("</body></html>")

        elif self.path.startswith('/data/'):

            p = self.path.split('/')

            self.ok_html()
            self.wfile.write("<html><head><link rel=\"stylesheet\" type=\"text/css\" href=\"/style.css\" /></head><body>")
            addr = address.fromConventional(p[2])
            self.wfile.write(name_form(addr))
            self.wfile.write(data_page(addr))
            self.wfile.write("</body></html>")

        elif self.path.startswith('/jump/'):

            p = self.path.split('/')

            self.ok_html()
            self.wfile.write("<html><head><link rel=\"stylesheet\" type=\"text/css\" href=\"/style.css\" /></head><body>")
            addr = address.fromConventional(p[2])
            self.wfile.write(name_form(addr))
            self.wfile.write(jumptable_page(addr))
            self.wfile.write("</body></html>")

        elif self.path == '/style.css':
            self.send_response(200)
            self.send_header('Content-type', 'text/css')
            self.end_headers()
            with open('style.css', 'r') as f:
                self.wfile.write(f.read())

        elif self.path.startswith('/set-name?'):
            q = urlparse(self.path).query
            p = parse_qs(q)
            print p, q
            addr = address.fromConventional(p['addr'][0])
            name = p['name'][0]
            tag.setNameForAddress(addr, name)
            self.redirect(self.headers['Referer'])

        else:
            self.send_response(404)
            self.end_headers()

def run():
    print len(database.getUnfinished()), 'unfinished'

    import traceback
    try:
        print ''
        #start_points = database.getAmbigCalls()
        #graph.save_dot(graph.getSubgraph(start_points))
        #database.produce_map()
        #graph.search()
    except Exception as e:
        print traceback.format_exc()

    #database.produce_map()

    server = HTTPServer(('', 8888), Handler)
    print "Running server..."
    server.serve_forever()

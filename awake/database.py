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

import sqlite3
import depend
import address
import procedure

connection = sqlite3.connect('data/xxx.db')

class ProcInfo(object):
    def __init__(self, addr, result=None):

        c = connection.cursor()
        c.execute('select type, depset, has_switch, suspicious_switch, has_suspicious_instr, has_nop, has_ambig_calls, length from procs where addr=?', (str(addr),))
        assert c.rowcount <= 1
        result = c.fetchone()

        self.addr = addr
        if result:
            self.type = result[0]
            self.depset = depend.decode(result[1])
            self.has_switch = result[2]
            self.suspicious_switch = result[3]
            self.has_suspicious_instr = result[4]
            self.has_nop = result[5]
            self.has_ambig_calls = result[6]
            self.length = result[7]
        else:
            self.type = "proc"
            self.depset = depend.unknown()
            self.has_switch = False
            self.suspicious_switch = False
            self.has_suspicious_instr = False
            self.has_nop = False
            self.has_ambig_calls = True
            self.length = 0

        self.calls = set()
        self.tail_calls = set()
        c.execute('select destination, type from calls where source=?', (str(addr),))
        for x in c.fetchall():
            if x[1] == 'tail':
                self.tail_calls.add(address.fromConventional(x[0]))
            else:
                self.calls.add(address.fromConventional(x[0]))

        self.memreads = set()
        self.memwrites = set()
        c.execute('select addr, type from memref where proc=?', (str(addr),))
        for x in c.fetchall():
            if x[1] == 'read':
                self.memreads.add(address.fromConventional(x[0]))
            else:
                self.memwrites.add(address.fromConventional(x[0]))

        self.callers = set()
        c.execute('select source from calls where destination=?', (str(addr),))
        for x in c.fetchall():
            self.callers.add(address.fromConventional(x[0]))

        c.close()

    def save(self):
        c = connection.cursor()
        c.execute('select addr from procs where addr=?', (str(self.addr),))
        if not c.fetchone():
            c.execute('insert into procs(addr) values (?)', (str(self.addr),))
        c.execute('update procs set type=?, depset=?, has_switch=?, suspicious_switch=?, has_suspicious_instr=? , has_nop=?, has_ambig_calls=?, length=? where addr=?',
                  (self.type, depend.encode(self.depset), int(self.has_switch), int(self.suspicious_switch), int(self.has_suspicious_instr), int(self.has_nop), int(self.has_ambig_calls), self.length, str(self.addr)))

        c.execute('delete from calls where source=?', (str(self.addr),))
        c.execute('delete from memref where proc=?', (str(self.addr),))

        for x in self.calls:
            c.execute('insert into calls(source, destination, type) values (?, ?, "call")', (str(self.addr), str(x)))
        for x in self.tail_calls:
            c.execute('insert into calls(source, destination, type) values (?, ?, "tail")', (str(self.addr), str(x)))
        for x in self.memreads:
            c.execute('insert into memref(addr, proc, type) values (?, ?, "read")', (str(x), str(self.addr)))
        for x in self.memwrites:
            c.execute('insert into memref(addr, proc, type) values (?, ?, "write")', (str(x), str(self.addr)))
        c.close()
        connection.commit()

    def html(self):
        out = ''
        import operand
        #out += operand.

def init():
    c = connection.cursor()
    c.execute('create table if not exists procs(addr text, type text, depset text, has_switch integer, suspicious_switch integer, has_suspicious_instr integer, has_nop integer, has_ambig_calls integer, length integer)')
    c.execute('create table if not exists calls(source text, destination text, type text)')
    c.execute('create table if not exists memref(addr text, proc text, type text)')
    c.close()
    connection.commit()

def procInfo(addr):
    return ProcInfo(addr)

def reportProc(addr):
    procInfo(addr).save()

def getProcByteOwner(byte_addr, ignore_addr=None):
    c = connection.cursor()
    c.execute('select addr from procs where addr<=? order by addr desc', (str(byte_addr),))
    result = c.fetchone()
    if not result:
        return None
    c.close()

    proc_addr = address.fromConventional(result[0])

    if proc_addr == ignore_addr:
        return None

    proc = procedure.at(proc_addr)

    if byte_addr not in proc.instructions:
        return None

    return proc_addr

def getNextOwnedAddress(addr):
    c = connection.cursor()
    c.execute('select addr from procs where addr > ? order by addr', (str(addr),))
    result = c.fetchone()
    c.close()
    if not result:
        return None
    return address.fromConventional(result[0])

init()

def getUnfinished():
    c = connection.cursor()
    c.execute('select addr from procs where has_ambig_calls=1 and suspicious_switch=0 and has_suspicious_instr=0')
    out = list()
    for result in c.fetchall():
        addr = address.fromConventional(result[0])
        out.append(addr)
    c.close()
    return out

def getAll():
    c = connection.cursor()
    c.execute('select addr from procs order by addr')
    out = list()
    for result in c.fetchall():
        addr = address.fromConventional(result[0])
        out.append(addr)
    c.close()
    return out

def setInitial(initial):
    c = connection.cursor()
    for x in initial:
        c.execute('insert into calls(source, destination) values ("FFFF:0000", ?)', (str(x),))
    c.close()
    connection.commit()

def getInteresting():
    import operand
    out = '<pre>'
    c = connection.cursor()
    c.execute('select addr from procs where has_ambig_calls=1')
    out += 'ambig calls:\n'
    for result in c.fetchall():
        addr = address.fromConventional(result[0])
        out += '    ' + operand.ProcAddress(addr).html() + '\n'
    c.execute('select addr from procs where suspicious_switch=1')
    out += 'suspicious switch:\n'
    for result in c.fetchall():
        addr = address.fromConventional(result[0])
        out += '    ' + operand.ProcAddress(addr).html() + '\n'
    c.execute('select addr from procs where has_suspicious_instr=1')
    out += 'suspicious instr:\n'
    for result in c.fetchall():
        addr = address.fromConventional(result[0])
        out += '    ' + operand.ProcAddress(addr).html() + '\n'
    c.close()
    out += '</pre>'
    return out

def getAmbigCalls():
    out = set()
    c = connection.cursor()
    c.execute('select addr from procs where has_ambig_calls=1')
    for result in c.fetchall():
        addr = address.fromConventional(result[0])
        out.add(addr)
    return out

def getDataReferers(data_addr):
    reads = set()
    writes = set()
    c = connection.cursor()
    c.execute('select proc, type from memref where addr=?', (str(data_addr),))
    for result in c.fetchall():
        addr = address.fromConventional(result[0])
        if result[1] == 'read':
            reads.add(addr)
        else:
            writes.add(addr)
    return reads, writes

def produce_map():

    romsize = 512*1024
    width = 256
    height = romsize/width

    import Image
    img = Image.new('RGB', (width, height))

    for i in range(512*1024):
        addr = address.fromPhysical(i)
        import disasm
        if addr.bank() in (0x08, 0x0C, 0x0D, 0x0E, 0x0F, 0x10, 0x11, 0x12, 0x13, 0x1C, 0x1D):
            color = (0, 0, 255)
        elif addr.bank() == 0x16 and addr.virtual() >= 0x5700:
            color = (0, 0, 255)
        elif addr.bank() == 0x09 and addr.virtual() >= 0x6700:
            color = (0, 0, 255)
        elif disasm.cur_rom.get(addr) == 0xFF:
            color = (0, 0, 127)
        else:
            color = (0, 0, 0)
        x = i % width
        y = i // width
        img.putpixel((x, y), color)

    c = connection.cursor()
    c.execute('select addr, length from procs order by addr')
    for result in c.fetchall():
        addr = address.fromConventional(result[0])
        length = result[1]

        for i in range(length):
            byte_addr = addr.offset(i).physical()

            x = byte_addr % width
            y = byte_addr // width
            color = (0, 255, 0)
            img.putpixel((x, y), color)

    c.close()

    img.save('data/ownership.png')
    print 'image saved'

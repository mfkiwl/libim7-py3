#!/usr/bin/python
# -*- coding: utf-8 -*-

#Copyright (C) 2010 Fabricio Silva

"""
This project intends to provide a simple pythonic interface to read 
Particle Image Velocimetry (PIV) image and vector fields files created 
by LaVision Davis software.
It bases on ctypes to build an object-oriented interface to their C library.
"""
import sys
import numpy as np
import ctypes as ct
import numpy.ctypeslib as nct

import os
try:
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "_im7")
except NameError:
    path = "./_im7"
    
if not(sys.platform in ('win32', 'cygwin')):
    path += '.cpython-34m.so'
    mylib = ct.cdll.LoadLibrary(path)
else:
    mylib = ct.cdll.LoadLibrary(path)

char16 = ct.c_char*16
word = ct.c_ushort
byte = ct.c_ubyte

# Error code returned by ReadIM7 C function
ImErr = {
    'IMREAD_ERR_NO':0,     'IMREAD_ERR_FILEOPEN':1, \
    'IMREAD_ERR_HEADER':2, 'IMREAD_ERR_FORMAT':3, \
    'IMREAD_ERR_DATA':4,   'IMREAD_ERR_MEMORY':5}

# Code for the buffer format
Formats = {
    'Formats_NOTUSED':-1, 'FormatsMEMPACKWORD':-2, \
    'FormatsFLOAT': -3,   'FormatsWORD':-4, \
    'FormatsDOUBLE':-5,   'FormatsFLOAT_VALID':-6, \
    'FormatsIMAGE':0,     'FormatsVECTOR_2D_EXTENDED':1, \
    'FormatsVECTOR_2D':2, 'FormatsVECTOR_2D_EXTENDED_PEAK':3,	\
    'FormatsVECTOR_3D':4, 'FormatsVECTOR_3D_EXTENDED_PEAK':5,	\
    'FormatsCOLOR':-10,   'FormatsRGB_MATRIX':-10, \
    'FormatsRGB_32':-11}
    
class BufferScale(ct.Structure):
    " Linear scaling tranform. "
    _fields_ = [("factor", ct.c_float), ("offset", ct.c_float),
                ("description", char16), ("unit", char16)]
    _fnames_ = [x[0] for x in _fields_]
    
    def _get_fdict(self):
        return dict( \
            [(x[0], self.__getattribute__(x[0])) for x in self._fields_])
    _fdict_ = property(_get_fdict)
    
    def __repr__(self):
        tmp = self.description.decode('utf-8') + " (%s)" % self.__class__
        tmp += ":\n\t(%.3f)*n+(%.3f)" %(self.factor, self.offset)
        if self.unit!="":
            tmp += " (%s)" % self.unit
        return tmp

    def __call__(self, vector, grid):
        if (isinstance(vector,int)):
            vector = np.arange(.5, vector)
        return vector*self.factor*grid+self.offset
    
    def setbufferscale(self, *args, **kwargs):
        latt = [tmp for tmp in self._fnames_ if not(tmp in list(kwargs.keys()))]
        dic = self._fdict_.copy()
        dic.update(kwargs)
        if len(args)<=len(latt):
            for ind,val in enumerate(args):
                dic[latt[ind]] = val
        else:
            print(args, kwargs)
            raise IOError("Too many arguments in _setbufferscale.")
        mylib.SetBufferScale(ct.byref(self), dic["factor"], dic["offset"], \
            ct.c_char_p(dic["description"]), ct.c_char_p(dic["unit"]))

class ImageHeaderX(ct.Structure):
    _pack_ = 2
    _fields_ = [ \
        ("imagetype", ct.c_short),      #0:  (Image_t)
        ("xstart", ct.c_short),         #2:  start-pos left, not used
        ("ystart", ct.c_short),         #4:  start-pos top, not used
        ("extended", ct.c_ubyte*4),      #6:  reserved
        ("rows", ct.c_short),           #10: total number of rows, if -1 the real number is stored in longRows
        ("columns", ct.c_short),        #12: total number of columns, if -1 see longColumns
        ("image_sub_type", ct.c_short), #14: type of image (int):
                                        #    (included starting from sc_version 4.2 on)
                                        #    0 = normal image
                                        #    1 = PIV vector field with header and 4*2D field rows = 9 * y-size
                                        #    2 = simple 2D vector field (not used yet)	    rows = 2 * y-size
                                        #    3 ...
        ("y_dim", ct.c_short),          #16: size of y-dim (size of x-dim is always = columns), not used
        ("f_dim", ct.c_short),          #18: size of f-dimension (number of frames)
        #for image_sub_type 1/2 only:
        ("vector_grid", ct.c_short),    #20: 1-n = vector data: grid size (included starting from sc_ver 4.2 on)
        ("ext", ct.c_char*11),          #22: reserved
        ("version", ct.c_ubyte),         #33:  e.g. 120 = 1.2	300+ = 3.xx  40-99 = 4.0 bis 9.9
        ]
    if 'win' in sys.platform:
        _fields_ += [ \
        ("date", ct.c_char*9),          #34
        ("time", ct.c_char*9)]          #43
    else:
        _fields_ += [ \
        ("date", ct.c_char*9),          #34
        ("time", ct.c_char*9)]          #43
    
    _fields_ += [ \
        ("xinit", ct.c_short),          #52:  x-scale values
        ("xa", ct.c_float),             #54
        ("xb", ct.c_float),             #58
        ("xdim", ct.c_char*11),         #62
        ("xunits", ct.c_char*11),       #73
        ("yinit", ct.c_short),          #84:  y-scale values
        ("ya", ct.c_float),             #86
        ("yb", ct.c_float),             #90
        ("ydim", ct.c_char*11),         #94
        ("yunits", ct.c_char*11),       #105
        ("iinit", ct.c_short),          #116:  intensity-scale values
        ("ia", ct.c_float),             #118
        ("ib", ct.c_float),             #122
        ("idim", ct.c_char*11),         #126
        ("iunits", ct.c_char*11),       #137
        ("com1", ct.c_char*40),         #148
        ("com2", ct.c_char*40),         #188
        ("longRows", ct.c_int),         #228 (large) number of rows, TL 04.02.2000
        ("longColumns", ct.c_int),      #232: (large) number of columns, TL 04.02.2000
        ("longZDim", ct.c_int),         #236: (large) number of z-dimension, TL 02.05.00
        ("reserved", ct.c_char*12),     #240: reserved
        ("checksum", ct.c_int)]        #252-255: not used
    
    def __repr__(self):
        tmp = "<%s.%s object at %s>\n" % (
            self.__class__.__module__,
            self.__class__.__name__, hex(id(self)))
        for k,v in self._fields_:
            if k is "reserved": continue
            try:
                tmp += "\t%s:\t%s\n" % (k, getattr(self, k))
            except:
                pass
        return tmp
        
class ImageHeader7(ct.Structure):
    _fields_ = [ \
        ("version", ct.c_short), \
        ("pack_type", ct.c_short), \
        ("buffer_format", ct.c_short), \
        ("isSparse", ct.c_short), \
        ("sizeX", ct.c_int), \
        ("sizeY", ct.c_int), \
        ("sizeZ", ct.c_int), \
        ("sizeF", ct.c_int), \
        ("scalarN", ct.c_short),  \
        ("vector_grid", ct.c_short),  \
        ("extraFlags", ct.c_short), \
        ("reserved", ct.c_byte*(256-30))]
    
    def __repr__(self):
        tmp = "<%s.%s object at %s>\n" % (
            self.__class__.__module__,
            self.__class__.__name__, hex(id(self)))
        for k,v in self._fields_:
            if k is "reserved": continue
            tmp += "\t%s:\t%s\n" % (k, getattr(self, k))
        return tmp

class _Data(ct.Union):
    _fields_ = [("floatArray", ct.POINTER(ct.c_float)), \
                ("wordArray",  ct.POINTER(ct.c_ushort))]

class Buffer(ct.Structure):
    _anonymous_ = ("array",)
    _fields_ = [("isFloat", ct.c_int), \
        ("nx", ct.c_int), ("ny", ct.c_int), \
        ("nz", ct.c_int), ("nf", ct.c_int), \
        ("totalLines", ct.c_int), \
        ("vectorGrid", ct.c_int), \
        ("image_sub_type", ct.c_int), \
        ("array", _Data), \
        ("scaleX", BufferScale), \
        ("scaleY", BufferScale), \
        ("scaleI", BufferScale)]
    
    def __repr__(self):
        tmp = "<%s.%s object at %s>\n" % (
            self.__class__.__module__,
            self.__class__.__name__, hex(id(self)))
        for k,v in self._fields_:
            tmp += "\t%s:\t%s\n" % (k, getattr(self, k))
        return tmp

    def read_header(self):
        try:
            #print(self.file)
            f = open(self.file, 'rb')
            tmp = f.read(ct.sizeof(ImageHeader7))
            f.close()
            self.header = ImageHeader7()
            ct.memmove(ct.addressof(self.header), ct.c_char_p(tmp), \
                ct.sizeof(ImageHeader7))
            assert self.header.sizeX==self.nx
            self.reader = "ReadIM7"
        except AssertionError:
            f = open(self.file, 'rb')
            tmp = f.read(ct.sizeof(ImageHeaderX))
            f.close()
            self.header = ImageHeaderX()
            ct.memmove(ct.addressof(self.header), ct.c_char_p(tmp), \
                ct.sizeof(ImageHeaderX))
            self.reader = "ReadIMX"
    
    def get_array(self):
        """ 
        Prepare data pointer to behave as a numpy array.
        rem: Should become obsolete with nct.prep_pointer.
        """
        try:
            self.array.__array_interface__
            return np.array(self.array, copy=False)
        except AttributeError:
            pass
            
        if self.isFloat==1:
            arr = self.floatArray
        else:
            arr = self.wordArray
        # Constructing array interface
        arr.__array_interface__ = {'version': 3, \
            'shape':(self.totalLines, self.nx), \
            'data': (ct.addressof(arr.contents), False),\
            'typestr' : nct._dtype(type(arr.contents)).str}
        return np.array(arr, copy=False)

    def __getattr__(self, key):
        if key=='header':
            self.read_header()
            return self.header
        elif key=='blocks':
            self.get_blocks()
            return self.blocks
        elif key in ('x', 'y', 'z'):
            self.get_positions()
            return self.__dict__[key]
        elif key in ('vx', 'vy', 'vz', 'vmag'):
            self.get_components()
            return self.__dict__[key]
        else:
            raise AttributeError("Does not have %s atribute" % key)
    
    def get_positions(self):
        self.x = self.scaleX(self.nx, self.vectorGrid)
        self.y = self.scaleY(self.ny, self.vectorGrid)
        if self.scaleY.factor<0:
            self.y = self.y[::-1]
        self.z = 0
        
    def get_blocks(self):
        " Transforms the concatenated blocks into arrays."
        h = self.header
        arr = self.get_array()
        if (self.reader is "ReadIMX") \
          or (h.buffer_format==Formats['FormatsIMAGE']):
            self.blocks = arr.reshape((self.nf, self.ny, self.nx))
        elif h.buffer_format>=1 and h.buffer_format<=5:
            nblocks = (9, 2, 10, 3, 14)
            nblocks = nblocks[h.buffer_format-1]
            self.blocks = arr.reshape((nblocks, -1, self.nx))
            self.ny = self.blocks.shape[1]
            if hasattr(self, 'y'): del self.y
        else:
            self.blocks = arr.reshape((self.nf*self.nz, self.ny, self.nx))
        #else:
        #    raise TypeError(u"Can't get blocks from this buffer format.")
    
    def get_frame(self, idx=0):
        """
        Extract the specified frame (index starting from 0).
        """
        if idx<self.nf:
            b = self.blocks
            return b[idx,...]
        else:
            raise ValueError('Buffer has no more than %d frames.' % self.nf)
    
    def get_components(self):
        """
        Extract the velocity components from the various blocks stored in
        Davis files according to values in the header.
        """
        h = self.header
        b = self.blocks
        ## TODO: check if there is still some magic behind choice.
        choice = np.array(b[0,:,:], dtype=int)
        if h.buffer_format==Formats['FormatsVECTOR_2D']:
            vx = b[0,:,:]
            vy = b[1,:,:]
            vz = np.zeros_like(vx)
        elif h.buffer_format==Formats['FormatsVECTOR_2D_EXTENDED']:
            vx = np.zeros(choice.shape, dtype=float)
            vy = np.zeros(choice.shape, dtype=float)
            vz = np.zeros(choice.shape, dtype=float)
            vx[choice==1] = b[1,:,:][choice==1]
            vx[choice==2] = b[3,:,:][choice==2]
            vx[choice==3] = b[5,:,:][choice==3]
            vx[choice==4] = b[7,:,:][choice==4]
            vx[choice==5] = b[7,:,:][choice==5] # post-processed
            vy[choice==1] = b[2,:,:][choice==1]
            vy[choice==2] = b[4,:,:][choice==2]
            vy[choice==3] = b[6,:,:][choice==3]
            vy[choice==4] = b[8,:,:][choice==4]
            vy[choice==5] = b[8,:,:][choice==5] # post-processed
        elif  h.buffer_format==Formats['FormatsVECTOR_2D_EXTENDED_PEAK']:
            vx = np.zeros(choice.shape, dtype=float)
            vy = np.zeros(choice.shape, dtype=float)
            vz = np.zeros(choice.shape, dtype=float)
            vx[choice==1] = b[1,:,:][choice==1]
            vx[choice==2] = b[3,:,:][choice==2]
            vx[choice==3] = b[5,:,:][choice==3]
            vx[choice==4] = b[7,:,:][choice==4]
            vx[choice==5] = b[7,:,:][choice==5] # post-processed
            vy[choice==1] = b[2,:,:][choice==1]
            vy[choice==2] = b[4,:,:][choice==2]
            vy[choice==3] = b[6,:,:][choice==3]
            vy[choice==4] = b[8,:,:][choice==4]
            vy[choice==5] = b[8,:,:][choice==5] # post-processed
            self.peak = b[9,:,:]
        elif h.buffer_format==Formats['FormatsVECTOR_3D']:
            vx = b[0,:,:]
            vy = b[1,:,:]
            vz = b[2,:,:]
        elif  h.buffer_format==Formats['FormatsVECTOR_3D_EXTENDED_PEAK']:
            vx = np.zeros(choice.shape, dtype=float)
            vy = np.zeros(choice.shape, dtype=float)
            vz = np.zeros(choice.shape, dtype=float)
            vx[choice==1] = b[1,:,:][choice==1]
            vx[choice==2] = b[4,:,:][choice==2]
            vx[choice==3] = b[7,:,:][choice==3]
            vx[choice==4] = b[10,:,:][choice==4]
            vx[choice==5] = b[10,:,:][choice==5] # post-processed
            vy[choice==1] = b[2,:,:][choice==1]
            vy[choice==2] = b[5,:,:][choice==2]
            vy[choice==3] = b[8,:,:][choice==3]
            vy[choice==4] = b[11,:,:][choice==4]
            vy[choice==5] = b[11,:,:][choice==5] # post-processed
            vz[choice==1] = b[3,:,:][choice==1]
            vz[choice==2] = b[6,:,:][choice==2]
            vz[choice==3] = b[9,:,:][choice==3]
            vz[choice==4] = b[12,:,:][choice==4]
            vz[choice==5] = b[12,:,:][choice==5] # post-processed
            self.peak = b[13,:,:]
        else:
            raise TypeError("Object does not have a vector field format.")
        
        # Davis indexing (y,x) => tranpose
        vx, vy, vz = vx.T, vy.T, vz.T
        
        # Davis conception of reversed y-axis
        if self.scaleY.factor>0:
            sl = [slice(None), slice(None)]
        else:
            print("im7: inverting axes y and z.")
            sl = [slice(None), slice(None,None, -1)]
            vy *= -1
            #vz *= -1
            
        self.vx = self.scaleI(vx, 1.)[sl]
        self.vy = self.scaleI(vy, 1.)[sl]
        self.vz = self.scaleI(vz, 1.)[sl]
        self.vmag = np.sqrt(self.vx**2+self.vy**2+self.vz**2)
    
    def delete(self):
        for key in ('x','y','z','vx','vy','vz','vmag','blocks'):
            if hasattr(self, key):
                setattr(self, key,None)
        del_buffer(self)
    
    def filter(self, fun=None, arrays=[]):
        """
        Mask vector fields with the result of the application of function fun
        taking a buffer as input argument. Returns velocity components
        as masked arrays, and may apply same process to other array arguments.
        """
        idx = fun(self)
        ff = lambda m: np.ma.array(m, mask=idx)
        lArrays = [self.vx, self.vy, self.vz]
        for tmp in arrays:
            if tmp.shape == self.vx.shape:
                lArrays.append(tmp)
            else:
                raise ValueError('Wrong shape for additional argument.')
        return list(map(ff, lArrays))
    
    def quiver_xyplane(self, ax=None, sep=1):
        ax = quiver_3d(self.x, self.y, self.vx, self.vy, self.vz, ax, sep)

            
class AttributeList(ct.Structure):
    def __getattr__(self, key):
        if key=='pairs':
            self.get_pairs()
            return self.pairs
        if key=='dict':
            return self.as_dict()
        else:
            raise AttributeError("Does not have %s atribute" % key)
            
    def get_pairs(self):
        att = self
        self.pairs = []
        while att!=0:
            try:
                self.pairs.append((att.name, att.value))
                att = att.next[0]
            except ValueError:
                break
    
    def as_dict(self):
        self.get_pairs()
        return dict(self.pairs)
        
    def delete(self):
        del_attributelist(self)
        
AttributeList._fields_ = [ \
    ("name", ct.c_char_p), \
    ("value", ct.c_char_p), \
    ("next", ct.POINTER(AttributeList))]

def imread_errcheck(retval, func, args):
    arg0 = ct.string_at(args[0])
    if func.__name__!="ReadIM7":
        raise ValueError("Wrong function passed: %s." % func.__name__)
    if retval==ImErr['IMREAD_ERR_FILEOPEN']:
        raise IOError("Can't open file %s." % arg0)
    elif retval==ImErr['IMREAD_ERR_HEADER']:
        raise ValueError("Incorrect header in file %s." % arg0)
    elif retval==ImErr['IMREAD_ERR_FORMAT']:
        raise IOError("Incorrect format in file %s." % arg0)
    elif retval==ImErr['IMREAD_ERR_DATA']:
        raise ValueError("Error while reading data in %s." % arg0)
    elif retval==ImErr['IMREAD_ERR_MEMORY']:
        raise MemoryError("Out of memory while reading %s." % arg0)
    else:
        pass

mylib.SetBufferScale.argtypes = [ct.POINTER(BufferScale), \
    ct.c_float, ct.c_float, ct.c_char_p, ct.c_char_p]
mylib.SetBufferScale.restype = None

mylib.ReadIM7.argtypes = [ct.c_char_p, ct.POINTER(Buffer), \
    ct.POINTER(ct.POINTER(AttributeList))]
mylib.ReadIM7.restype = ct.c_int
mylib.ReadIM7.errcheck = imread_errcheck

mylib.DestroyBuffer.argtypes = [ct.POINTER(Buffer),]
mylib.DestroyBuffer.restype = None
mylib.DestroyAttributeList.argtypes = [ct.POINTER(ct.POINTER(AttributeList)),]
mylib.DestroyAttributeList.restype = None

def readim7(filename, scale_warn= False):
    mybuffer = Buffer()
    att_pp = ct.pointer(AttributeList())
    filename=bytes(filename,'utf-8')
    mylib.ReadIM7(ct.c_char_p(filename), ct.byref(mybuffer), ct.byref(att_pp))
    mybuffer.file = filename.decode('utf-8')
    att = att_pp[0]
    def from_att(field):
        tmp = getattr(mybuffer,field)
        if getattr(tmp,'factor')==0 and getattr(tmp,'offset')==0:
            if scale_warn:
                print('%s not set in %s' % (field, filename))
            if field=='scaleX':
                attv = att.as_dict()['_SCALE_X']
            elif field=='scaleY':
                attv = att.as_dict()['_SCALE_Y']
            elif field=='scaleI':
                attv = att.as_dict()['_SCALE_I']
            else:
                return
            vals = attv.split(' ')
            setattr(tmp,'factor', float(vals[0]))
            vals = vals[1].split('\n')
            setattr(tmp,'offset', float(vals[0]))
            setattr(tmp,'unit', vals[1])
            setattr(tmp,'description', vals[2])
            
    mybuffer.get_blocks()
    from_att('scaleX')
    from_att('scaleX')
    from_att('scaleY')
    from_att('scaleI')
    if mybuffer.reader is 'ReadIMX':
        h = mybuffer.header
        mybuffer.scaleX = BufferScale(description=h.xdim, unit=h.xunits, 
            factor=h.xa, offset=h.xb)
        mybuffer.scaleY = BufferScale(description=h.ydim, unit=h.yunits, 
            factor=h.ya, offset=h.yb)
        
    return mybuffer, att

del_buffer = lambda self: mylib.DestroyBuffer(ct.byref(self))
del_attributelist = lambda self: mylib.DestroyAttributeList(ct.byref(ct.pointer(self)))

def save_as_pivmat(filename, buf, att=None):
    """
    Save single file data according to PIVMAT format
    http://www.fast.u-psud.fr/pivmat/html/pivmat_data.html
    """
    dic = {'namex':'x','namey':'y','namevx':'vx','namevy':'vy'}
    for key in ('x','y','z','vx','vy','vz','name', 'setname', 'source'):
        try:
            dic[key] = getattr(buf, key)
        except AttributeError:
            dic[key] = buf.__getattr__(key)
    dic['unitx'] = buf.scaleX.unit.strip('[]')
    dic['unity'] = buf.scaleY.unit.strip('[]')
    dic['unitvx'] = buf.scaleI.unit
    dic['unitvy'] = buf.scaleI.unit
    dic['choice'] = buf.blocks[0,:,:]
    vysign = {True:'Y axis downward', False:'Y axis upward'}
    dic['ysign'] = vysign[buf.scaleY.factor>0]
    
    dic['history'] = np.zeros((1,), dtype=np.object)
    dic['pivmat_version'] = 'unknown'
    # Still lacks following field: sourcename
    import scipy.io as io
    io.savemat(filename, dic)
    
def show_scalar_field(arr, extent=None, ax=None, colorbar=False):
    import matplotlib.pyplot as plt
    if ax==None:
        ax = plt.figure().add_subplot(111)
    im = ax.imshow(arr, interpolation='nearest', aspect='equal', origin='lower', \
        vmin=arr.min(), vmax=arr.max(), extent=extent)
    if colorbar:
        plt.colorbar(im)
    return ax

def quiver_3d(x,y,vx,vy,vz, ax=None, sep=1):
    import matplotlib.pyplot as plt
    if ax==None:
        ax = plt.figure().add_subplot(111)
    Q = ax.quiver(vy[::sep,::sep], vx[::sep,::sep], \
        vz[::sep,::sep], pivot='mid')
    qk = plt.quiverkey(Q, 0.9, 0.95, 5, r'$5 \frac{m}{s}$',
               labelpos='E',
               coordinates='figure',
               fontproperties={'weight': 'bold'})
    return ax

if __name__=='__main__':
    buf, att = readim7("./test/B00001.VC7")
    
    def myfilter(buf):
        return buf.blocks[0,:,:]!=5
#        V = buf.vmag
#        mean, std = V.mean(), V.std()
#        N = 1.5
#        return np.logical_or(V<mean-N*std, V>mean+N*std)
    
    show_scalar_field(buf.blocks[0,:,:])
    vx, vy, vz, vmag = buf.filter(myfilter, arrays=[buf.vmag,])
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm
    plt.figure()
    plt.quiver(buf.x,buf.y,vx, vy, vmag, cmap=cm.jet)
    plt.colorbar()
    plt.show()

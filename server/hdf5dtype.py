##############################################################################
# Copyright by The HDF Group.                                                #
# All rights reserved.                                                       #
#                                                                            #
# This file is part of H5Serv (HDF5 REST Server) Service, Libraries and      #
# Utilities.  The full HDF5 REST Server copyright notice, including          #
# terms governing use, modification, and redistribution, is contained in     #
# the file COPYING, which can be found at the root of the source code        #
# distribution tree.  If you do not have access to this file, you may        #
# request a copy from help@hdfgroup.org.                                     #
##############################################################################

"""
This class is used to map between HDF5 type representations and numpy types   
 
"""
import sys
import numpy as np
import h5py
import logging


"""
Convert the given type item  to a predefined type string for 
predefined integer and floating point types ("H5T_STD_I64LE", et. al).
For compound types, recursively iterate through the typeItem and do same
conversion for fields of the compound type.
"""    
def getTypeResponse(typeItem):
    response = None
    if 'uuid' in typeItem:
        # committed type, just return uuid
        response = typeItem['uuid']
    elif typeItem['class'] == 'H5T_INTEGER' or  typeItem['class'] == 'H5T_FLOAT':
        # just return the class and base for pre-defined types
        response = {}
        response['class'] = typeItem['class']
        response['base'] = typeItem['base']
    elif typeItem['class'] == 'H5T_OPAQUE':
        response = {}
        response['class'] = 'H5T_OPAQUE'
        response['size'] = typeItem['size']
    elif typeItem['class'] == 'H5T_REFERENCE':
        response = {}
        response['class'] = 'H5T_REFERENCE'
        response['base'] = typeItem['base']
    elif typeItem['class'] == 'H5T_COMPOUND':
        response = {}
        response['class'] = 'H5T_COMPOUND'
        fieldList = []
        for field in typeItem['fields']:
            fieldItem = { }
            fieldItem['name'] = field['name']
            fieldItem['type'] = getTypeResponse(field['type'])  # recursive call
            fieldList.append(fieldItem)
        response['fields'] = fieldList
    else:
        response = {}   # otherwise, return full type
        for k in typeItem.keys():
            if k == 'base':
                if type(typeItem[k]) == dict:
                    response[k] = getTypeResponse(typeItem[k])  # recursive call
                else:
                    response[k] = typeItem[k]  # predefined type
            elif k not in ('size', 'base_size'):
                response[k] = typeItem[k]
    return response
           
        
"""
    Return type info.
          For primitive types, return string with typename
          For compound types return array of dictionary items
"""
def getTypeItem(dt):
    type_info = {}
    if len(dt) <= 1:
        type_info = getTypeElement(dt)
    else:
        names = dt.names
        type_info['class'] = 'H5T_COMPOUND'
        fields = []
        for name in names:
            field = { 'name': name }
            field['type'] = getTypeElement(dt[name])  
            fields.append(field)
            type_info['fields'] = fields
    return type_info
             
"""
    Get element type info - either a complete type or element of a compound type
    Returns dictionary
    Note: only getTypeItem should call this!
"""
            
def getTypeElement(dt):
    if len(dt) > 1:
        raise Exception("unexpected numpy type passed to getTypeElement")
    
    type_info = {}
         
    if dt.kind == 'O':
        # numpy object type - assume this is a h5py variable length extension
        h5t_check = h5py.h5t.check_dtype(vlen=dt)
        if h5t_check is not None:
            type_info['base_size'] = 8  # machine pointer size
            if h5t_check == str:
                type_info['class'] = 'H5T_STRING'
                type_info['strsize'] = 'H5T_VARIABLE'
                type_info['cset'] = 'H5T_CSET_ASCII'
                type_info['strpad'] = 'H5T_STR_NULLTERM'
                type_info['order'] = 'H5T_ORDER_NONE'
            elif h5t_check == unicode:
                type_info['class'] = 'H5T_STRING'
                type_info['strsize'] = 'H5T_VARIABLE'
                type_info['cset'] = 'H5T_CSET_UTF8'
                type_info['strpad'] = 'H5T_STR_NULLTERM'
                type_info['order'] = 'H5T_ORDER_NONE'
            elif type(h5t_check) == np.dtype:
                # vlen data
                type_info['class'] = 'H5T_VLEN'
                type_info['size'] = 'H5T_VARIABLE'
                type_info['base'] = getBaseType(h5t_check)   
            else:
                #unknown vlen type
                raise Exception("Unknown h5py vlen type")
        else:
            # check for reference type
            h5t_check = h5py.h5t.check_dtype(ref=dt)
            if h5t_check is not None:
                type_info['class'] = 'H5T_REFERENCE'
                type_info['order'] = 'H5T_ORDER_NONE'
                basedt = None
                if h5t_check is h5py.h5r.Reference:
                    type_info['base'] = 'H5T_STD_REF_OBJ'  # objref
                elif h5t_check is h5py.h5r.RegionReference:
                    type_info['base'] = 'H5T_STD_REF_DSETREG'  # region ref
                else:
                    raise Exception("unexpected reference type")
            else:     
                raise Exception("unknown object type")
    elif dt.kind == 'V':
        baseType = getBaseType(dt)
        if dt.shape:
            # array type
            type_info['dims'] = dt.shape
            type_info['class'] = 'H5T_ARRAY'
            type_info['base'] = getBaseType(dt)
        elif baseType['class'] == 'H5T_OPAQUE':
            # expecting this to be an opaque type
            type_info = baseType  # just promote the base type
        else:
            raise Exception("unexpected Void type")
    elif dt.kind == 'S':
        # String type
        baseType = getBaseType(dt)
        type_info = baseType  # just use base type
    elif dt.kind == 'i':
        # integer type
        baseType = getBaseType(dt)
        # numpy integer type - but check to see if this is the hypy 
        # enum extension
        mapping = h5py.h5t.check_dtype(enum=dt)  
            
        if mapping:
            # yes, this is an enum!
            type_info['class'] = 'H5T_ENUM'
            type_info['mapping'] = mapping
            type_info['base'] = baseType
        else:
            type_info = baseType  # just use base type
    
    elif dt.kind == 'f':
        # floating point type
        baseType = getBaseType(dt)
        type_info = baseType  # just use base type
    else:
        # unexpected kind
        raise Exception("unexpected dtype kind: " + dt.kind)
        
    return type_info
        
"""
Get Base type info for given type element.
"""    
def getBaseType(dt):
    if len(dt) > 1:
        raise Exception("unexpected numpy type passed to getTypeElement")
             
    predefined_int_types = {
        'int8':    'H5T_STD_I8',
        'uint8':   'H5T_STD_UI8',
        'int16':   'H5T_STD_I16',
        'uint16':  'H5T_STD_UI16',
        'int32':   'H5T_STD_I32',
        'uint32':  'H5T_STD_UI32',
        'int64':   'H5T_STD_I64',
        'uint64':  'H5T_STD_UI64'
    }
    predefined_float_types = {
        'float32': 'H5T_IEEE_F32',
        'float64': 'H5T_IEEE_F64'
    }
    type_info = {}
    type_info['size'] = dt.itemsize
    type_info['base_size'] = dt.base.itemsize
         
    # primitive type
    if dt.base.kind == 'S':
        # Fixed length string type
        type_info['class'] = 'H5T_STRING' 
        type_info['cset'] = 'H5T_CSET_ASCII'
        type_info['strsize'] = dt.itemsize
        type_info['strpad'] = 'H5T_STR_NULLPAD'
        type_info['order'] = 'H5T_ORDER_NONE'
    elif dt.base.kind == 'V':
            type_info['class'] = 'H5T_OPAQUE'
            type_info['order'] = 'H5T_ORDER_NONE'
    elif dt.base.kind == 'i':    
        type_info['class'] = 'H5T_INTEGER'
        byteorder = 'LE'
        if dt.byteorder == '>':
            byteorder = 'BE'
        type_info['order'] = 'H5T_ORDER_' + byteorder
        if dt.base.name in predefined_int_types:
            #maps to one of the HDF5 predefined types
            type_info['base'] = predefined_int_types[dt.base.name] + byteorder  
    elif dt.base.kind == 'f':
        type_info['class'] = 'H5T_FLOAT'
        byteorder = 'LE'
        if dt.byteorder == '>':
            byteorder = 'BE'
        type_info['order'] = 'H5T_ORDER_' + byteorder
        if dt.base.name in predefined_float_types:
            #maps to one of the HDF5 predefined types
            type_info['base'] = predefined_float_types[dt.base.name] + byteorder 
    else:
        # unexpected kind
        raise Exception("unexpected dtype base kind: " + dt.base.kind)
    
    return type_info
 

def getNumpyTypename(hdf5TypeName, typeClass=None):
    predefined_int_types = {
          'H5T_STD_I8':   'i1', 
          'H5T_STD_UI8':  'u1',
          'H5T_STD_I16':  'i2', 
          'H5T_STD_UI16': 'u2',
          'H5T_STD_I32':  'i4', 
          'H5T_STD_UI32': 'u4',
          'H5T_STD_I64':  'i8',
          'H5T_STD_UI64': 'u8' 
    }
    predefined_float_types = {
          'H5T_IEEE_F32': 'f4',
          'H5T_IEEE_F64': 'f8'
    }
    if len(hdf5TypeName) < 3:
        raise Exception("Type Error: invalid type")
    endian = '<'  # default endian
    key = hdf5TypeName
    if hdf5TypeName.endswith('LE'):
        key = hdf5TypeName[:-2]
    elif hdf5TypeName.endswith('BE'):
        key = hdf5TypeName[:-2]
        endian = '>'
        
    if key in predefined_int_types and (typeClass == None or 
            typeClass == 'H5T_INTEGER'):
        return endian + predefined_int_types[key]
    if key in predefined_float_types and (typeClass == None or 
            typeClass == 'H5T_FLOAT'):
        return endian + predefined_float_types[key]
    raise Exception("Type Error: invalid type")
    
    
def createBaseDataType(typeItem):
    logging.info("createDatatype (" + str(typeItem) + ") type: " + str(type(typeItem)))
    dtRet = None
    if type(typeItem) == str or type(typeItem) == unicode:
        # should be one of the predefined types
        dtName = getNumpyTypename(typeItem)
        dtRet = np.dtype(dtName)
        return dtRet  # return predefined type
        
    if type(typeItem) != dict:
        raise Exception("Type Error: invalid type")
        
    if 'class' not in typeItem:
        raise Exception("Type Error: 'class' not provided")
    typeClass = typeItem['class']
    shape = ''
    if 'shape' in typeItem:  
        dims = None      
        if type(typeItem['shape']) == int:
            dims = (typeItem['shape'])  # make into a tuple
        elif type(typeItem['shape']) not in (list, tuple):
            raise Exception("Type Error: expected list or integer for shape")
        else:
            dims = typeItem['shape']
        shape = str(tuple(dims))
        
    if typeClass == 'H5T_INTEGER':
        if 'base' not in typeItem:
            raise Exception("Type Error: 'base' not provided")      
        baseType = getNumpyTypename(typeItem['base'], typeClass='H5T_INTEGER')
        dtRet = np.dtype(shape + baseType)
    elif typeClass == 'H5T_FLOAT':
        if 'base' not in typeItem:
            raise Exception("Type Error: 'base' not provided")
        baseType = getNumpyTypename(typeItem['base'], typeClass='H5T_FLOAT')
        dtRet = np.dtype(shape + baseType)
    elif typeClass == 'H5T_STRING':
        if 'strsize' not in typeItem:
            raise Exception("Type Error: 'strsize' not provided")
        if 'cset' not in typeItem:
            raise Exception("Type Error: 'cset' not provided")          
            
        if typeItem['strsize'] == 'H5T_VARIABLE':
            if shape:
                raise Exception(
                    "Type Error: ArrayType is not supported for variable len types")
            if typeItem['cset'] == 'H5T_CSET_ASCII':
                dtRet = h5py.h5t.special_dtype(vlen=str)
            elif typeItem['cset'] == 'H5T_CSET_UTF8':
                dtRet = h5py.h5t.special_dtype(vlen=unicode)
            else:
                raise Exception("Type Error: unexpected 'cset' value")
        else:
            nStrSize = typeItem['strsize']
            if type(nStrSize) != int:
                raise Exception("Type Error: expecting integer value for 'strsize'")
            dtRet = np.dtype(shape + 'S' + str(nStrSize))  # fixed size ascii string
    elif typeClass == 'H5T_VLEN':
        if shape:
            raise Exception(
                "Type Error: ArrayType is not supported for variable len types")
        if 'base' not in typeItem:
            raise Exception("Type Error: 'base' not provided") 
        baseType = getNumpyTypename(typeItem['base'])
        dtRet = h5py.h5t.special_dtype(vlen=np.dtype(baseType))
    elif typeClass == 'H5T_OPAQUE':
        if shape:
            raise Exception(
                "Type Error: Opaque Type is not supported for variable len types")
        if 'size' not in typeItem:
            raise Exception("Type Error: 'size' not provided")
        nSize = int(typeItem['size'])
        if nSize <= 0:
            raise Exception("Type Error: 'size' must be non-negative")
        dtRet = np.dtype('V' + str(nSize))
    elif typeClass == 'H5T_ARRAY':
        if not shape:
            raise Exception("Type Error: 'shape' must be provided for array types")
        if 'base' not in typeItem:
            raise Exception("Type Error: 'base' not provided") 
        baseType = getNumpyTypename(typeItem['base'])
        if type(baseType) not in  (str, unicode):
            raise Exception("Array type is only supported for predefined base types")
        # should be one of the predefined types
        dtRet = np.dtype(shape+baseType)
        return dtRet  # return predefined type     
    else:
        raise Exception("Type Error: Invalid type class")
        
      
    return dtRet  
    
def createDataType(typeItem):
    logging.info("createDatatype(" + str(typeItem) + ") type: " + str(type(typeItem)))
    
    dtRet = None
    if type(typeItem) == str or type(typeItem) == unicode:
        # should be one of the predefined types
        dtName = getNumpyTypename(typeItem)
        dtRet = np.dtype(dtName)
        return dtRet  # return predefined type
        
    if type(typeItem) != dict:
        raise Exception("Type Error: invalid type")
        
    if 'class' not in typeItem:
        raise Exception("Type Error: 'class' not provided")
    typeClass = typeItem['class']
    if typeClass == 'H5T_COMPOUND':
        if 'fields' not in typeItem:
            raise Exception("Type Error: 'fields' not provided for compound type")
        fields = typeItem['fields']
        if type(fields) is not list:
            raise Exception("Type Error: expected list type for 'fields'")
        if not fields:
            raise Exception("Type Error: no 'field' elements provided")
        subtypes = []
        for field in fields:
            if type(field) != dict:
                raise Exception("Type Error: invalid field")
            if 'name' not in field:
                raise Exception("Type Error: 'name' missing from field")
            if 'type' not in field:
                raise Exception("Type Error: 'type' missing from field")
            field_name = field['name']
            if type(field_name) == unicode:
                # convert to ascii
                ascii_name = field_name.encode('ascii')
                if ascii_name != field_name:
                    raise Exception("Type Error: none ascii field name not allowed")
                field['name'] = ascii_name
                
            dt = createDataType(field['type'])  # recursive call
            if dt is None:
                raise Exception("unexpected error")
            subtypes.append((field['name'], dt))  # append tuple
        dtRet = np.dtype(subtypes)
    else:
        dtRet = createBaseDataType(typeItem)  # create non-compound dt
    return dtRet
        
                
    
        
            
   
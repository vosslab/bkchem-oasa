#--------------------------------------------------------------------------
#     This file is part of BKChem - a chemical drawing program
#     Copyright (C) 2003-2008 Beda Kosata <beda@zirael.org>

#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     Complete text of GNU GPL can be found in the file LICENSE in the
#     main directory of the program

#--------------------------------------------------------------------------
#
#
#
#--------------------------------------------------------------------------

"""Module containing miscelanous functions used in BKChem that don't
fit anywhere else. Does not contain any objects.
"""

import re
import sys



def myisstr(obj: object) -> object:
  if sys.version_info[0] > 2:
    return isinstance(obj, str)
  else:
    return isinstance(obj, str)


def intersection( a: object, b: object) -> object:
  "returns intersection of 2 lists"
  ret = []
  for i in a:
    if i in b:
      ret.append( i)
  return ret


def difference( a: object, b: object) -> object:
  "returns difference of 2 lists ( a-b)"
  ret = list( a)  # needed for type conversion of tuple for instance
  for i in b:
    if i in ret:
      ret.remove( i)
  return ret


def signum( a: object) -> object:
  if a == 0:
    return 0
  elif a < 0:
    return -1
  else:
    return 1


def filter_unique( items: object) -> object:
  #t1 = time.time()
  ret = []
  for item in items:
    if item not in ret:
      ret.append( item)
  #print time.time() - t1
  return ret


#def sub_all_numbers( text):
#  return re.sub( "\d+", '<sub>\g<0><\\sub>', text)

def reverse_molecule_formula( formula: object) -> object:
  pass


def normalize_coords( coords: object) -> object:
  x1, y1, x2, y2 = coords
  if x2 < x1:
    x2, x1 = x1, x2
  if y2 < y1:
    y2, y1 = y1, y2
  return (x1, y1, x2, y2)


def list_difference( list: object) -> object:
  """return a list of differences between list members,
  the list is by 1 shorter than the original"""
  ret = []
  for i in range( len( list)-1):
    ret.append( list[i]-list[i+1])
  return ret


def split_number_and_unit( txt: object) -> object:
  try:
    v = float( txt)
    return v, ''
  except:
    pass
  cutter = re.compile( r"([+-]?\d*\.?\d*)\s*([a-zA-Z]*)")
  if txt:
    a = cutter.match( txt)
    if a and a.group(1):
      return float( a.group(1)), a.group(2)
  return None, None


def lazy_apply( function: object, arguments: object) -> object:
  """similar to apply but returns a callable (lambda) that performs the apply when called."""
  return lambda: function(*arguments)




def extend_bbox( bbox: object, pixels: object = 1) -> object:
  minx = min( (bbox[0], bbox[2]))
  maxx = max( (bbox[0], bbox[2]))
  miny = min( (bbox[1], bbox[3]))
  maxy = max( (bbox[1], bbox[3]))
  return minx-pixels, miny-pixels, maxx+pixels, maxy+pixels


def smallest_common_bbox( bboxes: object) -> object:
  _x0, _y0, _x1, _y1 = None, None, None, None
  for (x0, y0, x1, y1) in bboxes:
    minx = min( x0, x1)
    maxx = max( x0, x1)
    miny = min( y0, y1)
    maxy = max( y0, y1)
    if not _x0 or minx < _x0:
      _x0 = minx
    if not _x1 or maxx > _x1:
      _x1 = maxx
    if not _y0 or miny < _y0:
      _y0 = miny
    if not _y1 or maxy > _y1:
      _y1 = maxy
  return _x1, _y1, _x0, _y0






def has_one_value_only( iterable: object) -> object:
  if not iterable:
    return 0
  a = iterable[0]
  for i in iterable:
    if a != i:
      return 0
  return 1



def plural_or_singular( iterable: object) -> object:
  """useful for string construction such as 'you have %d apple%s' % (len(apples), plural_or_singular( apples)"""
  if len( iterable) == 1:
    return ''
  else:
    return 's'


def len_and_ending( iterable: object) -> object:
  return (len( iterable), plural_or_singular( iterable))


def reverse( iterable: object) -> object:
  for i in range( len( iterable)-1, -1, -1):
    yield iterable[i]



# some helper, higher order functions

map_functions = lambda funcs, value: [lazy_apply(func, (value,)) for func in funcs]

something_true = lambda vals: len( [_f for _f in vals if _f])

some_apply = lambda func, vals: something_true( list(map( func, vals)))



# some results

isinstance_of_one = lambda obj, parents: some_apply( lambda x: isinstance( obj, x), parents)




def gen_variations(items: object, n: object) -> object:
  if n==0:
    yield []
  else:
    for i in range( len(items)-n+1):
      for v in gen_variations(items[i+1:],n-1):
        yield [items[i]]+v


def gen_combinations( items: object, n: object) -> object:
  if n==0:
    yield []
  else:
    for i in range( len( items)):
      for v in gen_combinations( [x for x in items if x!=items[i]], n-1):
        yield [items[i]]+v


def x_over_y( x: object, y: object) -> object:
  return factorial( x) / factorial( y) / factorial( x-y)


def factorial( x: object) -> object:
  ret = 1
  for i in range( 2, x+1):
    ret *= i
  return ret


def gen_variations_and_one( items: object, length: object) -> object:
  for i in items:
    vars = gen_variations( [x for x in items if x!=i], length-1)
    for vs in vars:
      yield vs + [i]

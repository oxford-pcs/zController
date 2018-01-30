import codecs
from decimal import *

import numpy as np
import pylab as plt

def decode(fname, encoding):
  '''
    Decode file with given encoding.
  '''
  fp = codecs.open(fname, "r", encoding)
  content = fp.readlines()
  fp.close()
  return content

class zCFFftPsf():
  '''
    Parse a Zemax FFT PSF output file.
  '''
  def __init__(self, fname, verbose=True, debug=False):
    self.fname = fname
    self.header = {"WAVE": None, "FIELD": None, "WAVE_EXP": None, 
                   "DATA_SPACING": None, "DATA_SPACING_EXP": None, 
                   "DATA_AREA": None, "DATA_AREA_EXP": None, 
                   "PGRID_SIZE": None, "IGRID_SIZE": None, "CENTRE": None}
    self.data = None 
    self.verbose = verbose
    self.debug = debug
          
  def _parseFileData(self, sampling):
    '''
      Read file data into a Numpy array.
    '''
    content = decode(self.fname, "UTF-16-LE")
    data = []
    for idx, line in enumerate(content):
      try:
        if idx>=18:
          data.append([float(i.rstrip('\r\n')) for i in line.split('\t')])  
      except TypeError:		# some non-floatable value has been found
        return False
    self.data = np.array(data)
    if not sampling == self.data.shape:	# not the same as expected sampling
      return False
    return True     

  def _parseFileHeader(self):
    '''
      Read file header contents into a dict.
    '''
    content = decode(self.fname, "UTF-16-LE")
    for idx, line in enumerate(content):
      if idx == 8:
        self.header['WAVE'] = float(line.split()[0].strip())
        if unicode(line.split()[1].rstrip(',').strip()) == u'm':
          self.header['WAVE_EXP'] = 1
        if unicode(line.split()[1].rstrip(',').strip()) == u'mm':
          self.header['WAVE_EXP'] = 1e-3
        elif unicode(line.split()[1].rstrip(',').strip()) == u'\xb5m':
          self.header['WAVE_EXP'] = 1e-6
        elif unicode(line.split()[1].rstrip(',').strip()) == u'nm':
          self.header['WAVE_EXP'] = 1e-9
        self.header['FIELD'] = (float(line.split()[3].rstrip(',').strip()), 
                                float(line.split()[4].strip()))
      elif idx == 9:
        self.header['DATA_SPACING'] = float(line.split()[3].strip())
        if unicode(line.split()[4].rstrip('.').strip()) == u'm':
          self.header['DATA_SPACING_EXP'] = 1
        if unicode(line.split()[4].rstrip('.').strip()) == u'mm':
          self.header['DATA_SPACING_EXP'] = 1e-3
        elif unicode(line.split()[4].rstrip('.').strip()) == u'\xb5m':
          self.header['DATA_SPACING_EXP'] = 1e-6
        elif unicode(line.split()[4].rstrip('.').strip()) == u'nm':
          self.header['DATA_SPACING_EXP'] = 1e-9
      elif idx == 10:
        self.header['DATA_AREA'] = float(line.split()[3].strip())
        if unicode(line.split()[4].strip()) == u'm':
          self.header['DATA_AREA_EXP'] = 1
        if unicode(line.split()[4].strip()) == u'mm':
          self.header['DATA_AREA_EXP'] = 1e-3
        elif unicode(line.split()[4].strip()) == u'\xb5m':
          self.header['DATA_AREA_EXP'] = 1e-6
        elif unicode(line.split()[4].strip()) == u'nm':
          self.header['DATA_AREA_EXP'] = 1e-9
      elif idx == 13:
        self.header['PGRID_SIZE'] = (int(line.split()[3].strip()), 
                                     int(line.split()[5].strip()))
      elif idx == 14:
        self.header['IGRID_SIZE'] = (int(line.split()[3].strip()), 
                                     int(line.split()[5].strip()))
      elif idx == 15:
        self.header['CENTRE'] = (int(line.split()[4].rstrip(',').strip()), 
                                 int(line.split()[6].strip()))
        
      if None in self.header.viewvalues():  # it's fully populated 
        return False
      return True
  
  def getData(self):
    return np.array(self.data)  
  
  def getHeader(self):
    return self.header 
 
  def parse(self):
    ''' 
      Parse the file fully.
    '''
    if self._parseFileHeader():
      if self.verbose:
        print "Successfully parsed ZEMAX FFT PSF output file header."
      if self.debug:
        print self.header
      if self._parseFileData(self.header['IGRID_SIZE']):
        if self.debug:
          plt.imshow(self.data)
          plt.colorbar()
          plt.show()
        if self.verbose:
          print "Successfully parsed ZEMAX FFT PSF output file data."
      else:
        print "Failed to parse ZEMAX FFT PSF output file data."
        return False
    else:
      print "Failed to read ZEMAX FFT PSF output file header." 
      return False
    return True 
 
class zCSystemData():
  '''
    Parse a Zemax FFT PSF system data file.
  '''
  def __init__(self, fname, verbose=True, debug=False):
    self.fname = fname
    self.header = {"WFNO": None, "EPD": None}
    self.verbose = verbose
    self.debug = debug
    
    self._parse()
  
  def _parseFileHeader(self):
    '''
      Read file header contents into a dict.
    '''
    content = decode(self.fname, "UTF-16-LE")
    for idx, line in enumerate(content):
      if len(line.split(':')) >= 2:
        if "Working F/#" in line.split(':')[0]:
          self.header['WFNO'] = float(line.split(':')[1].strip())
        elif "Entrance Pupil Diameter" in line.split(':')[0]:
          self.header['EPD'] = float(line.split(':')[1].strip())
    if None in self.header.viewvalues():		# it's fully populated
      return False
    return True
  
  def getHeader(self):
    return self.header
  
  def parse(self):
    ''' 
      Parse the file fully.
    '''
    if self._parseFileHeader():
      if self.verbose:
        print "Successfully parsed ZEMAX system data file header."
      if self.debug:
        print self.header
    else:
      print "Failed to parse ZEMAX system data file header."
      return False
    
class zCWFE():
  '''
    Parse a Zemax wavefront error map.
  '''
  def __init__(self, fname, verbose=True, debug=False):
    self.fname = fname
    self.header = {"WAVE": None, "FIELD": None, "WAVE_EXP": None, "P2V": None, 
                   "RMS": None, "EXIT_PUPIL_DIAMETER": None, "SAMPLING": None, 
                   "CENTRE": None}
    self.data = None 
    self.verbose = verbose
    self.debug = debug

  def _parseFileData(self, sampling):
    '''
      Read file data into a Numpy array.
    '''
    content = decode(self.fname, "UTF-16-LE")
    data = []
    for idx, line in enumerate(content):
      try:
        if idx>=16:
          data.append([float(i.rstrip('\r\n')) for i in line.split('\t')])  
      except TypeError:		# some non-floatable value has been found
        return False
    self.data = np.array(data)
    if not sampling == self.data.shape:	# not the same as expected sampling
      return False
    return True   
    
  def _parseFileHeader(self):
    '''
      Read file header contents into a dict.
    '''
    content = decode(self.fname, "UTF-16-LE")
    for idx, line in enumerate(content):
      if idx == 8:
        self.header['WAVE'] = Decimal(line.split()[0].strip())
        if unicode(line.split()[1].rstrip(',').strip()) == u'm':
          self.header['WAVE_EXP'] = Decimal('1')
        if unicode(line.split()[1].rstrip(',').strip()) == u'mm':
          self.header['WAVE_EXP'] = Decimal('1e-3')
        elif unicode(line.split()[1].rstrip(',').strip()) == u'\xb5m':
          self.header['WAVE_EXP'] = Decimal('1e-6')
        elif unicode(line.split()[1].rstrip(',').strip()) == u'nm':
          self.header['WAVE_EXP'] = Decimal('1e-9')
        self.header['FIELD'] = (float(line.split()[3].rstrip(',').strip()), 
                                float(line.split()[4].strip()))
      elif idx == 9:
        self.header['P2V'] = float(line.split()[4].strip())
        self.header['RMS'] = float(line.split()[8].strip())
      elif idx == 11:
        self.header['EXIT_PUPIL_DIAMETER'] = float(line.split()[3].strip())
        self.header['EXIT_PUPIL_DIAMETER_UNIT'] = str(line.split()[4].strip())
      if idx == 13:
        self.header['SAMPLING'] = (int(line.split()[3].strip()), 
                                    int(line.split()[5].strip()))
      if idx == 14:
        self.header['CENTRE'] = (int(line.split()[4].rstrip(',').strip()), 
                                  int(line.split()[6].strip()))
    if None in self.header.viewvalues():		# it's fully populated
      return False
    return True

  def getData(self):
   return self.data 

  def getHeader(self):
    return self.header 
 
  def parse(self):
    '''
      Parse a file fully.
    '''
    if self._parseFileHeader():
      if self.verbose:
        print "Successfully parsed ZEMAX WFE output file header."
      if self.debug:
        print self.header
      if self._parseFileData(self.header['SAMPLING']):
        if self.debug:
          plt.imshow(self.data)
          plt.colorbar()
          plt.show()
        if self.verbose:
          print "Successfully parsed ZEMAX WFE output file data."
      else:
        print "Failed to parse ZEMAX WFE output file data."
        return False
    else:
      print "Failed to read ZEMAX WFE output file header." 
      return False
    return True

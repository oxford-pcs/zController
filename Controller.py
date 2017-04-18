class ControllerFunctionError(Exception):
  def __init__(self, message, error):
    super(Exception, self).__init__(message)
    self.errors = error

class Controller():
  '''
    This class wraps some of the functionality from pyZDDE into more convenient 
    functions, ensuring that the DDE and LDE are always in sync.
  '''
  def __init__(self, zmx_link):
    self.zmx_link = zmx_link
    
  def _updateDDE(self):
    self.zmx_link.zOptimize(numOfCycles=-1)
    self.zmx_link.zGetUpdate()
    
  def DDEToLDE(self):
    self._updateDDE()
    self.zmx_link.zPushLens()

  def LDEToDDE(self):
    self.zmx_link.zGetRefresh()
    self._updateDDE()

  def addTiltAndDecentre(self, start_surf, end_surf, x_c, y_c, x_tilt, y_tilt):   
    '''
      Add coordinate breaks for tilt (x_tilt, y_tilt) and decentre (x_c, y_c).
    '''
    cb1, cb2, dummy = self.zmx_link.zTiltDecenterElements(start_surf,
                                                          end_surf, 
                                                          xdec=x_c, 
                                                          ydec=y_c, 
                                                          xtilt=x_tilt, 
                                                          ytilt=y_tilt)
    self.DDEToLDE()
    return (cb1, cb2, dummy)
  
  def doOptimise(self, nCycles=0):
    mf_value = self.zmx_link.zOptimize(numOfCycles=nCycles, algorithm=0, 
                                       timeout=60)
    return mf_value   
  
  def doRaytrace(self, wave_number=1, mode=0, surf=-1, hx=0, hy=0, px=0, py=0):
    '''
      wave_number     wavelength number as in the wavelength data editor
      mode            0 = real; 1 = paraxial
      surf            surface to trace the ray to. Usually, the ray data is only
                      needed at the image surface; setting the surface number to
                      -1 will yield data at the image surface.
      hx              normalised field height along x axis
      hy              normalised field height along y axis
      px              normalised height in pupil coordinate along x axis
      py              normalised height in pupil coordinate along y axis
    '''
    return self.zmx_link.zGetTrace(wave_number, mode, surf, hx, hy, px, py)

  def getSurfaceComment(self, surf):
    return self.zmx_link.zGetSurfaceData(surf, self.zmx_link.SDAT_COMMENT) 
  
  def getCoordBreakDecentreX(self, surf):
    return self.zmx_link.zGetSurfaceParameter(surf, 1)
  
  def getCoordBreakDecentreY(self, surf):
    return self.zmx_link.zGetSurfaceParameter(surf, 2)
  
  def getCoordBreakTiltX(self, surf):
    return self.zmx_link.zGetSurfaceParameter(surf, 3)
  
  def getCoordBreakTiltY(self, surf):
    return self.zmx_link.zGetSurfaceParameter(surf, 4)

  def getLensData(self):
    return self.zmx_link.zGetFirst()

  def getWavelength(self, index_in_wavelength_table=0):
    return self.zmx_link.zGetWave(index_in_wavelength_table)

  def getSystemData(self):
    return self.zmx_link.zGetSystem()
    
  def getThickness(self, surf):
    return self.zmx_link.zGetSurfaceData(surf, 
                                         self.zmx_link.SDAT_THICK)
  
  def loadZemaxFile(self, path):
    self.zmx_link.zLoadFile(path)
    self.zmx_link.zPushLens()
    
  def loadMeritFunction(self, filename):
    self.zmx_link.zLoadMerit(filename)

  def saveMeritFunction(self, filename):
    self.zmx_link.zSaveMerit(filename)
      
  def setCoordBreakDecentreX(self, surf, value):
    return self.zmx_link.zSetSurfaceParameter(surf, 1, value)
  
  def setCoordBreakDecentreY(self, surf, value):
    return self.zmx_link.zSetSurfaceParameter(surf, 2, value)
  
  def setCoordBreakTiltX(self, surf, value):
    return self.zmx_link.zSetSurfaceParameter(surf, 3, value)
  
  def setCoordBreakTiltY(self, surf, value):
    return self.zmx_link.zSetSurfaceParameter(surf, 4, value)  

  def setFieldNumberOf(self, n_fields):
    self.zmx_link.zSetSystemProperty(101, n_fields)
    self.DDEToLDE()
    
  def setFieldType(self, field_type=0):
    '''
      Set field type from enumeration:
    
      0   object angle,
      1   object height, 
      2   paraxial image height,
      3   real image height
    '''
    if field_type >= 0 or field_type <= 3:
      self.zmx_link.zSetSystemProperty(100, field_type)  
    else:
      raise ControllerFunctionError("Invalid field type", -1)
  
  def setFieldValue(self, field_x, field_y, index_in_field_table=1):
    self.zmx_link.zSetSystemProperty(102, index_in_field_table, field_x)
    self.zmx_link.zSetSystemProperty(103, index_in_field_table, field_y)
    self.DDEToLDE()
    
  def setSolveCoordBreakDecentres(self, surf, solve_type=1):
    '''
      Set solve type for coordinate break decentres from enumeration:
    
      0   fixed,
      1   variable
    '''
    if solve_type == 0:
      stype = self.zmx_link.SOLVE_PAR0_VAR
    elif solve_type == 1:
      stype = self.zmx_link.SOLVE_PAR0_FIXED
    else:
      raise ControllerFunctionError("Unknown solve type.", -1)
    
    self.zmx_link.zSetSolve(surf, self.zmx_link.SOLVE_SPAR_PAR1, stype)
    self.zmx_link.zSetSolve(surf, self.zmx_link.SOLVE_SPAR_PAR2, stype)
    self.DDEToLDE()   
  
  def setSolveCoordBreakTilts(self, surf, solve_type=1):
    '''
      Set solve type for coordinate break tilts from enumeration:
    
      0   fixed,
      1   variable
    '''  
    if solve_type == 0:
      stype = self.zmx_link.SOLVE_PAR0_VAR
    elif solve_type == 1:
      stype = self.zmx_link.SOLVE_PAR0_FIXED
    else:
      raise ControllerFunctionError("Unknown solve type.", -1)
    
    self.zmx_link.zSetSolve(surf, self.zmx_link.SOLVE_SPAR_PAR3, stype)
    self.zmx_link.zSetSolve(surf, self.zmx_link.SOLVE_SPAR_PAR4, stype)
    self.DDEToLDE()   
    
  def setSurfaceComment(self, surf, comment, append=False):
    if append:
      old_comment = self.getSurfaceComment(surf)
      if old_comment is not "":
        comment = comment + ';' + old_comment
    self.zmx_link.zSetSurfaceData(surf, self.zmx_link.SDAT_COMMENT, 
                                  comment)
    self.DDEToLDE()
    
  def setSurfaceThicknessSolveVariable(self, surf):
    self.zmx_link.zSetSolve(surf, self.zmx_link.SOLVE_SPAR_THICK, 
                            self.zmx_link.SOLVE_THICK_VAR)
    self.DDEToLDE()

  def setupFieldsTable(self, fields, field_type=0):
    '''
      Populate the fields table with the data from [fields].
      
      [fields] must be a list of tuples, (field_x, field_y), in the format of 
      [field_type] (see setFieldType).

      Returns: Dictionary of field number mapped to physical field.
    '''
    self.setNumberOfFields(len(fields))
    self.setFieldType(field_type)
    res = {}
    for index, field in enumerate(fields):
      self.setField(field[0], field[1], index+1)
      res[index+1] = (field[0], field[1])
    return res

  def setupWavelengthsTable(self, wav_start, wav_end, wav_inc):
    '''
      Populate the wavelengths table with wavelengths starting from [wav_start],
      finishing with [wav_end] and with an increment of [wav_inc]. Units, as per
      Zemax default, are microns.
      
      Returns: Dictionary of wavelength number mapped to physical wavelength.
    '''
    n_waves = ((wavelength_end - wavelength_start)/wavelength_increment)+1
    self.setNumberOfWavelengths(n_waves)
    res = {}
    for index, wave in enumerate(np.arange(wavelength_start, wavelength_end+
                                           wavelength_increment, wavelength_end, 
                                           dtype=Decimal)):
      self.setWavelength(wave, index+1)
      res[index+1] = wave
    return res

  def setWavelengthNumberOf(self, n_waves):
    self.zmx_link.zSetSystemProperty(201, n_waves)
    self.DDEToLDE()
    
  def setWavelengthValue(self, wave, index_in_wavelength_table=1):
    self.zmx_link.zSetSystemProperty(202, index_in_wavelength_table, wave)
    self.DDEToLDE()
    

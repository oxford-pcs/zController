class ControllerFunctionError(Exception):
  def __init__(self, message, error):
    super(Exception, self).__init__(message)
    self.errors = error

class Controller():
  '''
    This class wraps the functionality from pyZDDE into more convenient 
    functions.
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
    
  def addTiltAndDecentre(self, start_surface_number, end_surface_number, 
                         x_decentre, y_decentre, x_tilt, y_tilt):
    cb1, cb2, dummy = self.zmx_link.zTiltDecenterElements(start_surface_number,
                                                          end_surface_number, 
                                                          xdec=x_decentre, 
                                                          ydec=y_decentre, 
                                                          xtilt=x_tilt, 
                                                          ytilt=y_tilt)
    self.DDEToLDE()
    return (cb1, cb2, dummy)
  
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

  def getSurfaceComment(self, surface_number):
    return self.zmx_link.zGetSurfaceData(surface_number, self.zmx_link.SDAT_COMMENT) 
  
  def getCoordBreakDecentreX(self, surface_number):
    return self.zmx_link.zGetSurfaceParameter(surface_number, 1)
  
  def getCoordBreakDecentreY(self, surface_number):
    return self.zmx_link.zGetSurfaceParameter(surface_number, 2)
  
  def getCoordBreakTiltX(self, surface_number):
    return self.zmx_link.zGetSurfaceParameter(surface_number, 3)
  
  def getCoordBreakTiltY(self, surface_number):
    return self.zmx_link.zGetSurfaceParameter(surface_number, 4)

  def getWavelength(self, wave=0):
    '''
      0 is the primary wavelength.
    '''
    return self.zmx_link.zGetWave(wave)

  def getSystemData(self):
    return self.zmx_link.zGetSystem()
    
  def getThickness(self, surface_number):
    return self.zmx_link.zGetSurfaceData(surface_number, self.zmx_link.SDAT_THICK)
  
  def loadFile(self, path):
    self.zmx_link.zLoadFile(path)
    self.zmx_link.zPushLens()
    
  def loadMF(self, filename):
    self.zmx_link.zLoadMerit(filename)

  def optimise(self, nCycles=0):
    mf_value = self.zmx_link.zOptimize(numOfCycles=nCycles, algorithm=0, timeout=60)
    return mf_value    
  
  def saveMF(self, filename):
    self.zmx_link.zSaveMerit(filename)
    
  def setComment(self, surface_number, comment, append=False):
    if append:
      old_comment = self.getSurfaceComment(surface_number)
      if old_comment is not "":
        comment = comment + ';' + old_comment
    self.zmx_link.zSetSurfaceData(surface_number, self.zmx_link.SDAT_COMMENT, comment)
    self.DDEToLDE()
    
  def setCoordBreakDecentreX(self, surface_number, value):
    return self.zmx_link.zSetSurfaceParameter(surface_number, 1, value)
  
  def setCoordBreakDecentreY(self, surface_number, value):
    return self.zmx_link.zSetSurfaceParameter(surface_number, 2, value)
  
  def setCoordBreakTiltX(self, surface_number, value):
    return self.zmx_link.zSetSurfaceParameter(surface_number, 3, value)
  
  def setCoordBreakTiltY(self, surface_number, value):
    return self.zmx_link.zSetSurfaceParameter(surface_number, 4, value)  

  def setField(self, field_x, field_y, index_in_field_table=1):
    self.zmx_link.zSetSystemProperty(102, index_in_field_table, field_x)
    self.zmx_link.zSetSystemProperty(103, index_in_field_table, field_y)
    self.DDEToLDE() 
  
  def setNumberOfFields(self, n_fields):
    self.zmx_link.zSetSystemProperty(101, n_fields)
    self.DDEToLDE()
    
  def setNumberOfWavelengths(self, n_waves):
    self.zmx_link.zSetSystemProperty(201, n_waves)
    self.DDEToLDE()
  
  def setSurfaceCoordBreakDecentresSolveVariable(self, surface_number):
    self.zmx_link.zSetSolve(surface_number, self.zmx_link.SOLVE_SPAR_PAR1, self.zmx_link.SOLVE_PAR0_VAR)
    self.zmx_link.zSetSolve(surface_number, self.zmx_link.SOLVE_SPAR_PAR2, self.zmx_link.SOLVE_PAR0_VAR)
    self.DDEToLDE()   
  
  def setSurfaceCoordBreakTiltsSolveVariable(self, surface_number):
    self.zmx_link.zSetSolve(surface_number, self.zmx_link.SOLVE_SPAR_PAR3, self.zmx_link.SOLVE_PAR0_VAR)
    self.zmx_link.zSetSolve(surface_number, self.zmx_link.SOLVE_SPAR_PAR4, self.zmx_link.SOLVE_PAR0_VAR)
    self.DDEToLDE()   
    
  def setSurfaceThicknessSolveVariable(self, surface_number):
    self.zmx_link.zSetSolve(surface_number, self.zmx_link.SOLVE_SPAR_THICK, self.zmx_link.SOLVE_THICK_VAR)
    self.DDEToLDE()
    
  def setWavelength(self, wave, index_in_wavelength_table=1):
    self.zmx_link.zSetSystemProperty(202, index_in_wavelength_table, wave)
    self.DDEToLDE()
    

    
    
    
  
    

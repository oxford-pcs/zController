import numpy as np
import os
import tempfile

from Parser import *

class ControllerFunctionError(Exception):
  def __init__(self, message, error):
    super(Exception, self).__init__(message)
    self.errors = error

class Controller():
  '''
    This class wraps some of the controller functionality from pyZDDE into more 
    convenient functions.
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

  def addTiltAndDecentre(self, start_surf, end_surf, x_c, y_c, x_tilt, y_tilt, order=0):   
    '''
      Add coordinate breaks for tilt (x_tilt, y_tilt) and decentre (x_c, y_c) 
      around the front surface.
    '''
    cb1, cb2, dummy = self.addTiltAndDecentreFromPivot(start_surf, end_surf, 
                                                       0, x_c, y_c, 
                                                       x_tilt, y_tilt, order)
    self.DDEToLDE()
    return (cb1, cb2, dummy)
  
  def addTiltAndDecentreAboutPivot(self, firstSurf, lastSurf, pivot_z=0, x_c=0.0, y_c=0.0, x_tilt=0.0, y_tilt=0.0, order=0):
    '''
      A tilt and decentre can be constructed by the following sequence:
      
      - Add a new surface, s1, with thickness set to the distance to the pivot 
        from the front of the lens.
      - Add coordinate break with tilts/decentres, with a thickness returning 
        from the excursion of s1 (PICKUP with a scale of -1).
      - Add surfaces between start_surf and end_surf
      - Thickness on last surface of lens is replaced with a position solve 
        to the position of the pivot, i.e. cb1.
      - Add a second coordinate break, cb2, returning to the original coordinate 
        system, the thickness of which is picked up from the last surface (which
        moved from the rear of the lens to the pivot) as the inverse, thus 
        moving to the rear surface of the lens again.
      - Add a dummy surface, dummy, after the second coordinate break with a 
        thickness of the original last surface.
          
      order:
      
        0 = decenter then tilt
        1 = tilt then decenter
        
    ''' 
    
    numSurfBetweenCBs = lastSurf - firstSurf + 1
    
    # Define new surface numbers
    s1 = firstSurf
    cb1 = firstSurf + 1
    cb2 = cb1 + numSurfBetweenCBs + 1
    dummy = cb2 + 1
    
    # Store the thickness and solve on thickness (if any) of the last surface 
    thick = self.zmx_link.zGetSurfaceData(surfNum=lastSurf, 
                                          code=self.zmx_link.SDAT_THICK)
    solve = self.zmx_link.zGetSolve(surfNum=lastSurf, 
                                    code=self.zmx_link.SOLVE_SPAR_THICK)
    
    # Insert required surfaces
    self.zmx_link.zInsertSurface(surfNum=s1)  # Movement to pivot
    self.zmx_link.zInsertSurface(surfNum=cb1) # 1st cb
    self.zmx_link.zInsertSurface(surfNum=cb2) # 2nd cb to restore axes
    self.zmx_link.zInsertSurface(surfNum=dummy) # Dummy after 2nd cb for dist
    
    # Add comments to surfaces
    self.zmx_link.zSetSurfaceData(surfNum=s1, code=self.zmx_link.SDAT_COMMENT,
                                  value="Move to pivot")
    self.zmx_link.zSetSurfaceData(surfNum=cb1, code=self.zmx_link.SDAT_COMMENT, 
                                  value='Element tilt and return from pivot')
    self.zmx_link.zSetSurfaceData(surfNum=cb1, code=self.zmx_link.SDAT_TYPE, 
                                  value='COORDBRK')
    self.zmx_link.zSetSurfaceData(surfNum=cb2, code=self.zmx_link.SDAT_COMMENT, 
                                  value='Element tilt return and move to rear')
    self.zmx_link.zSetSurfaceData(surfNum=cb2, code=self.zmx_link.SDAT_TYPE, 
                                  value='COORDBRK')
    self.zmx_link.zSetSurfaceData(surfNum=cb2, code=self.zmx_link.SDAT_COMMENT, 
                                  value='Return to pivot')
    self.zmx_link.zSetSurfaceData(surfNum=dummy, code=self.zmx_link.SDAT_COMMENT, 
                                  value='Dummy distance')
        
    # Transfer thickness of the surface just before the cb2 (originally 
    # lastSurf) to the dummy surface to retain inter-lens distance
    lastSurf += 2  # last surface number incremented by 2 because of cb1+s1
    self.zmx_link.zSetSurfaceData(surfNum=lastSurf, 
                                  code=self.zmx_link.SDAT_THICK, 
                                  value=0.0)
    self.zmx_link.zSetSolve(lastSurf, 
                            self.zmx_link.SOLVE_SPAR_THICK, 
                            self.zmx_link.SOLVE_THICK_FIXED)
    self.zmx_link.zSetSurfaceData(surfNum=dummy, 
                                  code=self.zmx_link.SDAT_THICK, 
                                  value=thick)
    
    # Transfer the solve on the thickness (if any) of the surface just before
    # the cb2 (originally lastSurf) to the dummy surface. The param1 of 
    # solve type "Thickness" may need to be modified before transferring.
    if solve[0] in {5, 7, 8, 9}: # param1 is a integer surface number
        param1 = int(solve[1]) if solve[1] < cb1 else int(solve[1]) + 1
    else: # param1 is a floating value, or macro name
        param1 = solve[1]
    self.zmx_link.zSetSolve(dummy, self.zmx_link.SOLVE_SPAR_THICK, solve[0], 
                            param1, solve[2], solve[3], solve[4])
    
    # Use pick-up solve on glass surface of dummy to pickup from lastSurf
    self.zmx_link.zSetSolve(dummy, self.zmx_link.SOLVE_SPAR_GLASS, 
                            self.zmx_link.SOLVE_GLASS_PICKUP,
                            lastSurf)
    
    # Use pick-up solves on second CB; set scale factor of -1 to lock the second
    # cb to the first.
    pickupcolumns = range(6, 11)
    params = [self.zmx_link.SOLVE_SPAR_PAR1, self.zmx_link.SOLVE_SPAR_PAR2, 
              self.zmx_link.SOLVE_SPAR_PAR3, self.zmx_link.SOLVE_SPAR_PAR4, 
              self.zmx_link.SOLVE_SPAR_PAR5]
    offset, scale = 0, -1
    for para, pcol in zip(params, pickupcolumns):
        self.zmx_link.zSetSolve(cb2, para, self.zmx_link.SOLVE_PARn_PICKUP, 
                                cb1, offset, scale, pcol)   
        
    # Set thickness of s1 to be the pivot point    
    self.zmx_link.zSetSolve(s1, self.zmx_link.SOLVE_SPAR_THICK, 
                            self.zmx_link.SOLVE_THICK_FIXED)
    self.zmx_link.zSetSurfaceData(surfNum=s1, code=self.zmx_link.SDAT_THICK, 
                                  value=pivot_z)
    
    # Use thickness pickup on cb1 to trace back from the pivot point to 
    # where the lens will start
    self.zmx_link.zSetSolve(cb1, self.zmx_link.SOLVE_SPAR_THICK, 
                            self.zmx_link.SOLVE_THICK_PICKUP, s1, -1, 0, 0)
    
    # Use thickness position solve on lastSurf to track back to the pivot point 
    # (where cb1 is) after lenses have been constructed
    self.zmx_link.zSetSolve(lastSurf, self.zmx_link.SOLVE_SPAR_THICK, 
                            self.zmx_link.SOLVE_THICK_POS, cb1, 0)
    
    # Use inverse pickup thickness solve on cb2 to restore position to lastSurf
    self.zmx_link.zSetSolve(cb2, self.zmx_link.SOLVE_SPAR_THICK, 
                            self.zmx_link.SOLVE_THICK_PICKUP, lastSurf, -1, 0, 
                            0)
    
    # Set the appropriate orders on the surfaces
    if order:
        cb1Ord, cb2Ord = 1, 0
    else:
        cb1Ord, cb2Ord = 0, 1
    self.zmx_link.zSetSurfaceParameter(surfNum=cb1, param=6, value=cb1Ord)    
    self.zmx_link.zSetSurfaceParameter(surfNum=cb2, param=6, value=cb2Ord)
    
    # Set the decenter and tilt values in the first cb
    params = range(1, 6)
    values = [x_c, y_c, x_tilt, y_tilt, 0]
    for par, val in zip(params, values):
        self.zmx_link.zSetSurfaceParameter(surfNum=cb1, param=par, value=val)
    self.zmx_link.zGetUpdate()
    
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

  def doRayTraceForFields(self, fields, field_type, wave_number=1, px=0, py=0):
    '''
      Trace rays for fields [fields] of type [field_type] at wavelength 
      [wave_number] as defined in the wavelength data editor.
      
      This routine circumvents the 12 field limitation.

      The output is in local coordinates for the surface defined by 
      [surf] in the doRayTrace() call.
    '''
    
    # find the maximum radial field coordinates, required to define hx and hy, 
    # the normalised field coordinates.
    #
    max_radial_field_index = np.argmax([np.sqrt((xy[0]**2)+(xy[1]**2)) 
                                        for xy in fields]) 
    max_radial_field_xy = fields[max_radial_field_index]
    max_radial_field_value = np.sqrt((max_radial_field_xy[0]**2)+ \
      (max_radial_field_xy[1]**2))
    
    # set up a field table with two fields, [0, 0] and [max_radial_field_x, 
    # max_radial_field_y].
    #
    self.setFieldsTable([(0,0), 
                         (max_radial_field_xy[0], max_radial_field_xy[1])], 
                        field_type=field_type)
    
    # now ray trace each field in [fields] normalised by the 
    # max_radial_field_value
    #
    rays = []
    for idx, f in enumerate(fields):
      if max_radial_field_value == 0:
        this_hx = 0
        this_hy = 0
      else:
        this_hx = f[0]/max_radial_field_value
        this_hy = f[1]/max_radial_field_value

      ray = self.doRaytrace(wave_number=wave_number, mode=0, surf=-1, 
                            hx=this_hx, hy=this_hy, px=px, py=py)
      rays.append(ray)
     
    return rays

  def getAnalysisWFE(self, field_number=1, wave_number=1, sampling=4):
    '''
      Returns a parsed WFE map for field [field_idx] and wavelength 
      [wave_number] as defined in the wavelength data editor.
      
      The WFE map sampling, [sampling], is 1 indexed, i.e.
      
      1 = 32 x 32
      2 = 64 x 64
      3 = 128 x 128
      .
      .
      Returns both the data and file header.
    '''
    fp_wfe, fp_wfe_filename = tempfile.mkstemp(suffix=".test")
    fp_wfe_settings, fp_wfe_settings_filename = tempfile.mkstemp(suffix=".CFG")
    try:
      # this first call generates a settings file that can be modified later
      assert self.zmx_link.zGetTextFile(fp_wfe_filename, "Wfm", 
                                        fp_wfe_settings_filename, 
                                        flag=0, timeout=None) == 0
      assert self.zmx_link.zModifySettings(fp_wfe_settings_filename, 
                                          "WFM_SAMP", 4) == 0
      assert self.zmx_link.zModifySettings(fp_wfe_settings_filename, 
                                           "WFM_FIELD", 
                                          field_number) == 0
      assert self.zmx_link.zModifySettings(fp_wfe_settings_filename, 
                                           "WFM_WAVE", 
                                          wave_number) == 0
      assert self.zmx_link.zGetTextFile(fp_wfe_filename, "Wfm", 
                                        fp_wfe_settings_filename, 
                                        flag=1, timeout=None) == 0
    except AssertionError:
      print "FATAL: Failed to construct WFE map."
      os.close(fp_wfe)
      os.close(fp_wfe_settings)
      return False
    
    wfe_parsed = zCWFE(fp_wfe_filename, verbose=False)
    try:
      assert wfe_parsed.parse() == True
    except AssertionError:
      print "FATAL: Failed to parse WFE map in Python data structures."
      os.close(fp_wfe)
      os.close(fp_wfe_settings)
      return False  
        
    os.close(fp_wfe)
    os.close(fp_wfe_settings)
    
    return wfe_parsed.getData(), wfe_parsed.getHeader()

  def getAnalysisWFEForFields(self, fields, field_type, wave_number=1, sampling=4):
    '''
      Get WFE maps for for fields [fields] of type [field_type] with wavelength 
      [wave_number] as defined in the wavelength data editor.
      
      This routine circumvents the 12 field limitation.
    '''
    
    # set up one field in the table
    #
    self.setFieldsNumberOf(1)
    self.setFieldType(field_type)
    
    # now get the WFE for each field point.
    #
    wfe_data = []
    wfe_headers = []
    for idx, f in enumerate(fields):
      self.setFieldValue(f[0], f[1])
      self.getAnalysisWFE()
      wfe_data.append(wfe_data)
      wfe_headers.append(wfe_headers)
     
    return wfe_data, wfe_headers

  def getCoordBreakDecentreX(self, surf):
    return self.zmx_link.zGetSurfaceParameter(surf, 1)
  
  def getCoordBreakDecentreY(self, surf):
    return self.zmx_link.zGetSurfaceParameter(surf, 2)
  
  def getCoordBreakTiltX(self, surf):
    return self.zmx_link.zGetSurfaceParameter(surf, 3)
  
  def getCoordBreakTiltY(self, surf):
    return self.zmx_link.zGetSurfaceParameter(surf, 4)

  def getField(self, field_number=0):
    return self.zmx_link.zGetField(field_number)  

  def getLensData(self):
    return self.zmx_link.zGetFirst()

  def getSurfaceComment(self, surf):
    return self.zmx_link.zGetSurfaceData(surf, self.zmx_link.SDAT_COMMENT) 

  def getSurfaceThickness(self, surf):
    return self.zmx_link.zGetSurfaceData(surf, self.zmx_link.SDAT_THICK)
  
  def getSystemData(self):
    return self.zmx_link.zGetSystem()
    
  def getWavelength(self, wave_number=0):
    return self.zmx_link.zGetWave(wave_number)  
  
  def isFileAlreadyLoaded(self, file_pathname):
    if self.zmx_link.zGetFile() == file_pathname:
      return True
    else:
      return False
  
  def loadZemaxFile(self, path):
    self.zmx_link.zLoadFile(path)
    self.zmx_link.zPushLens()

  def saveZemaxFile(self, path):
    self.zmx_link.zSaveFile(path) 
    
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

  def setFieldsNumberOf(self, n_fields): 
    try:
      assert n_fields <= 12
    except AssertionError:
      print "WARNING: Tried to insert too many fields into field table,",
      print "entries will be truncated"
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
  
  def setFieldValue(self, field_x, field_y, field_number=1):
    self.zmx_link.zSetSystemProperty(102, field_number, field_x)
    self.zmx_link.zSetSystemProperty(103, field_number, field_y)
    self.DDEToLDE()
    
  def setFieldsTable(self, fields, field_type=0):
    '''
      Populate the fields table with the data from [fields].
      
      [fields] must be a list of tuples, (field_x, field_y), in the format of 
      [field_type] (see setFieldType). The number of fields is limited to 12.

      Returns dictionary of field number mapped to physical field.
    '''
    self.setFieldsNumberOf(len(fields))
    self.setFieldType(field_type)
    res = {}
    for index, field in enumerate(fields):
      self.setFieldValue(field[0], field[1], index+1)
      res[index+1] = (field[0], field[1])
    return res    
    
  def setSolveCoordBreakDecentres(self, surf, solve_type=1):
    '''
      Set solve type for coordinate break decentres from enumeration:
    
      0   fixed,
      1   variable
    '''
    if solve_type == 0:
      stype = self.zmx_link.SOLVE_PAR0_FIXED
    elif solve_type == 1:
      stype = self.zmx_link.SOLVE_PAR0_VAR
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
      stype = self.zmx_link.SOLVE_PAR0_FIXED
    elif solve_type == 1:
      stype = self.zmx_link.SOLVE_PAR0_VAR
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

  def setWavelengthNumberOf(self, n_waves):
    try:
      assert n_waves <= 24
    except AssertionError:
      print "WARNING: Tried to insert too many wavelengths into field table,",
      print "entries will be truncated..."
    self.zmx_link.zSetSystemProperty(201, n_waves)
    self.DDEToLDE()
    
  def setWavelengthValue(self, wave, wave_number=1):
    self.zmx_link.zSetSystemProperty(202, wave_number, wave)
    self.DDEToLDE()
    
  def setWavelengthsTable(self, wav_start, wav_end, wav_inc):
    '''
      Populate the wavelengths table with wavelengths starting from [wav_start],
      finishing with [wav_end] and with an increment of [wav_inc]. Units, as per
      Zemax default, are microns. The number of wavelengths is limited to 24.
      
      Returns a dictionary of wavelength number mapped to physical wavelength.
    '''
    n_waves = ((wavelength_end - wavelength_start)/wavelength_increment)+1
    self.setWavelengthsNumberOf(n_waves)
    res = {}
    for index, wave in enumerate(np.arange(wavelength_start, wavelength_end+
                                           wavelength_increment, wavelength_end, 
                                           dtype=Decimal)):
      self.setWavelengthValue(wave, index+1)
      res[index+1] = wave
    return res

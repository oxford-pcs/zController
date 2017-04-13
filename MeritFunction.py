class MeritFunctionError(Exception):
  def __init__(self, message, error):
    super(Exception, self).__init__(message)
    self.errors = error

class MeritFunction():
  '''
    This class provides functionality to create a merit function 
    using Zemax's command DEFAULTMERIT.
    
    To create a merit fnction, a blank (or not, it will be 
    overwritten) ZPL file is required to be placed in the macros 
    directory of your Zemax distribution. This file cannot be 
    created on-the-fly as Zemax only populates its available macro 
    list at runtime.
  '''
  
  def __init__(self, zmx_link, lens_data, mfe_zpl_path, mfe_zpl_filename):
    self.zmx_link = zmx_link
    self.lens_data = lens_data
    self.mfe_zpl_path = mfe_zpl_path
    self.mfe_zpl_filename = mfe_zpl_filename
      
  def _constructCommand(self, atype=0, data=0, reference=0, method=1, 
                        rings=8, arms=3, grid=8, delete=0, axial=-1, 
                        lateral=1, start=-1, xweight=1, oweight=1, 
                        pup_obsc=0):
    '''
      Write the ZPL parsable command to the .ZPL file.
    
      atype       use 0 for RMS, 1, for PTV.
      data        use 0 for wavefront, 1 for spot radius, 2 for spot x, 
                  3 for spot y, 4 for spot x + y.
      reference   use 0 for centroid, 1 for chief, 2 for unreferenced.
      method      use 1 for Gaussian quadrature, 2 for rectangular array.
      rings       the number of annular rings (Gaussian quadrature only).
      arms        the number of radial arms (Gaussian quadrature only). 
                  The number of arms must be even and no less than 6.
      grid        the size of the grid. Use an integer, such as 8, for an 
                  8 x 8 grid. n must be even and no less than 4.
      delete      use 0 to not delete vignetted rays, 1 to delete 
                  vignetted rays.
      axial       use -1 for automatic, which will use symmetry only if 
                  the system is axial symmetric. Use 1 to assume axial 
                  symmetry, 0 to not assume axial symmetry.
      lateral     use 1 to ignore lateral color, 0 otherwise.
      start       use -1 for automatic, which will add the default merit 
                  function after any existing DMFS operand. Otherwise use 
                  the operand number at which to add the default merit 
                  function. Any existing operands above the specified 
                  operand number will be retained.
      xweight     the x direction weight (only spot x+y),
      oweight     the overall weight for the merit function. 
      pup_obsc	the pupil obscuration ratio.
      
    '''
    try:
      with open(self.mfe_zpl_path + self.mfe_zpl_filename, 'w') as f:
        MF_parameters = ["DEFAULTMERIT", str(atype), str(data), 
                          str(reference), str(method), str(rings),
                          str(arms), str(grid), str(delete), str(axial),
                          str(lateral), str(start), str(xweight), 
                          str(oweight), str(pup_obsc)]    
        f.write("CLOSEWINDOW\n")
        f.write(', '.join(MF_parameters))
    except IOError:
      raise MeritFunctionError(".ZPL file could not be found at this \
          path.", 1)    
    
  def _getMFEContents(self):
    '''
      Get MFE contents.
    '''
    self.zmx_link.zInsertMFO(1)
    n_operands = self.zmx_link.zDeleteMFO(1)     
    contents = self.zmx_link.ipzGetMFE(end_row=n_operands, pprint=False)
    return contents
  
  def _DDEToLDE(self):
    self.lens_data.DDEToLDE()

  def _LDEToDDE(self):
    self.lens_data.LDEToDDE()

  def createDefaultMF(self, atype=0, data=1, reference=0, method=1, 
                      rings=3, arms=3, grid=8, delete=0, axial=0, 
                      lateral=1, start=-1, xweight=1, oweight=1, 
                      pup_obsc=0):
    '''
      Create a default Merit Function and place it in the DDE.
      
      See _constructCommand() for parameter explanations.
    '''
    
    # Make .ZPL command and write to macro
    self._constructCommand(atype, data, reference, method, rings, arms, 
                           grid, delete, axial, lateral, start, xweight, 
                           oweight, pup_obsc)
    
    # Execute command and move data from LDE to DDE. Note that executing 
    # a macro only updates the LDE and so we need to update the DDE 
    # to access the updated function.
    #
    zpl_code = self.mfe_zpl_filename[0:3]
    rtn_code = self.zmx_link.zExecuteZPLMacro(zpl_code)
    self._LDEToDDE() 
      
  def delMFOperand(self, row_number):
    '''
      Delete a MF operand from the MFE.
    '''
    self.zmx_link.zDeleteMFO(row_number)
    self._LDEToDDE()
    
  def getRowNumberFromMFContents(self, oper, comment=None):
    '''
      Get row number number of an operand in the MFE given the 
      operand name and (optionally) comment.
    '''
    for idx, row in enumerate(self._getMFEContents()):
      if row.Oper == oper:
        if comment is not None and row.int1 == comment:
          return idx+1
        else:
          return idx+1
    return 0
      
  def setAirGapConstraints(self, ins_row_number, surface_number, min_gap, 
                           max_gap):
    '''
      Add air gap constraints.
    '''
    self.zmx_link.zInsertMFO(ins_row_number)
    self.zmx_link.zSetOperandRow(ins_row_number, "MNCA", int1=surface_number, 
                                  int2=surface_number, data1=None, 
                                  data2=None, data3=None, data4=None, 
                                  data5=None, data6=None, tgt=min_gap, 
                                  wgt=1.0)
    self.zmx_link.zInsertMFO(ins_row_number)
    self.zmx_link.zSetOperandRow(ins_row_number, "MXCA", int1=surface_number, 
                                  int2=surface_number, data1=None, 
                                  data2=None, data3=None, data4=None, 
                                  data5=None, data6=None, tgt=max_gap, 
                                  wgt=1.0)          
    self._DDEToLDE()

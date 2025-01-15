
import os
import sys
import csv
import math
from math import sqrt, floor
import random
import array

from ij import IJ, ImagePlus, Prefs, WindowManager
from ij.process import ImageProcessor, FloatProcessor, ByteProcessor, ImageStatistics, ImageConverter
from ij.gui import GenericDialog, NonBlockingGenericDialog, Overlay, TextRoi
from ij.plugin import Duplicator, ImageCalculator, Zoom
from ij.measure import Measurements, ResultsTable
from ij.plugin.frame import RoiManager

from java.io import File
from java.awt import Font, Color
import java.util.Arrays as Arrays
from javax.swing import JOptionPane, JFileChooser

from fiji.util.gui import GenericDialogPlus

from loci.plugins import BF
from loci.plugins.in import ImporterOptions
from loci.formats import MetadataTools, ImageReader
from ij.plugin.filter import GaussianBlur
from java.io import FileOutputStream, OutputStreamWriter
from java.nio.charset import StandardCharsets

# -*- coding: utf-8 -*-
reload(sys)
sys.setdefaultencoding('utf-8')


# Defining some constants
Plugin_Name = "QCScope"
Function_Name = "Field Uniformity"
Unicode_Micron_Symbol = "u" #chr(0xB5)
Reset_Preferences = False # Usefull to reset Preferences with the template
User_Desktop_Path = os.path.join(os.path.expanduser("~"), "Desktop") # Used for Saving the Output DIrectory and as a default for selecting an input directory
Output_Dir = os.path.join(User_Desktop_Path, "Output") # Where all files are saved

# Tuple (List) of supported image file extensions. When an input folder is selected only images with these extensions are selected
Image_Valid_Extensions = (".tif", ".tiff", ".jpg", ".jpeg", ".png", ".czi", ".nd2", ".lif", ".lsm", ".ome.tif", ".ome.tiff")

# Provide possilble space units and an normalized correspondance
Space_Unit_Conversion_Dictionary = {
	"micron": Unicode_Micron_Symbol + "m",
	"microns":Unicode_Micron_Symbol + "m",
	Unicode_Micron_Symbol + "m": Unicode_Micron_Symbol + "m",
	"um": Unicode_Micron_Symbol + "m",
	"u": Unicode_Micron_Symbol + "m",
	"nm": "nm",
	"nanometer": "nm",
	"nanometers": "nm",
	"mm": "mm",
	"millimeter": "mm",
	"millimeters": "mm",
	"cm": "cm",
	"centimeter": "cm",
	"centimeters": "cm",
	"m": "m",
	"meter": "m",
	"meters": "m",
	"inch": "in",
	"inches": "in",
	"in": "in",
	"pixel": "pixels",
	"pixels": "pixels",
	"": "pixels",
	}

# Dictionnary of Settings
Settings_Templates_List={
"Field_Uniformity.Settings_Template": {
	"Field_Uniformity.Gaussian_Blur": True,
	"Field_Uniformity.Gaussian_Sigma": 10.0,
	"Field_Uniformity.Binning_Method": "Iso-Density",
	"Field_Uniformity.BatchMode": False,
	"Field_Uniformity.Save_Individual_Files": True,
	"Field_Uniformity.ProlixMode": True
	},

"Microscope_Settings_Template": {
	"Field_Uniformity.Microscope_Objective_Mag": "5x",
	"Field_Uniformity.Microscope_Objective_NA": 1.0,
	"Field_Uniformity.Microscope_Objective_Immersion": "Air",
	"Field_Uniformity.Microscope_Channel_Names": ["DAPI", "Alexa488", "Alexa555", "Alexa647", "Alexa730","Alexa731","Alexa732","Alexa733"],
	"Field_Uniformity.Microscope_Channel_WavelengthsEM": [425, 488, 555, 647, 730, 731, 732, 733]
	}
}


# Some Usefull functions

# Make Sure to get all measurements are selected in ImageJ
IJ.run("Set Measurements...", "area mean standard modal min centroid center perimeter bounding fit shape feret's integrated median skewness kurtosis area_fraction stack redirect=None decimal=3");

# Display a message in the log only in ProlixMode
def Prolix_Message(Message):
	Field_Uniformity_Settings_Stored=Read_Preferences(Settings_Templates_List["Field_Uniformity.Settings_Template"])
	if Field_Uniformity_Settings_Stored["Field_Uniformity.ProlixMode"]:
		IJ.log(Message)

# Check if Setting in the Setting List are in the Preferences. If not, write them from the Templates. Also used to Reset Settings
def Initialize_Preferences(Settings_Templates_List, Reset_Preferences):
	for SettingsGroup in Settings_Templates_List.keys():
	 	for Setting, Value in Settings_Templates_List[SettingsGroup].items():
		 	if Prefs.get(Setting, None) is None:
				Save_Preferences(Settings_Templates_List[SettingsGroup])
 				break
		if Reset_Preferences:
			Save_Preferences(Settings_Templates_List[SettingsGroup])
	return None

# Read the Preferences an return a dictionnary with the settings
def Read_Preferences(Settings_Template):
	Preferences_Stored = {}
	for key, default_value in Settings_Template.items():
		value = Prefs.get(key, str(default_value))
		# Use the Type of data defined from the Settings Template to convert the settings from the Pref in the correct type
		if isinstance(default_value, bool):
			value = bool(int(value))
		elif isinstance(default_value, float):
			value = float(value)
		elif isinstance(default_value, int):
			value = int(value)
		elif isinstance(default_value, list):
			if isinstance(default_value[0], int):
	 			value = [int(round(float(item))) for item in value.split(",")]
			elif isinstance(default_value[0], float):
				value = [float(item) for item in value.split(",")]
			else:
				value = [str(item) for item in value.split(",")]
		else:
			value = str(value)
		Preferences_Stored[key] = value
	return Preferences_Stored # A dictionary of the Settings

# Save Settings in the Preference File
def Save_Preferences(Settings):
	for key, value in Settings.items():
		if isinstance(value, list):
			value = ",".join(map(str, value)) # If the value is a list join it with ","
		elif isinstance(value, bool):
			value = int(value) # If the value is boolean convert to integer because for some reasone writing False as string does not work
		else:
			value = value
		Prefs.set(key, str(value)) # Write the Preferences as strings
	Prefs.savePreferences()

# Get Images either from the opened ones or from a selected folder.
# Return Image_List a list of ImageTitle OR a List of File path
def Get_Images():
	Prolix_Message("Getting Images...")
	if WindowManager.getImageTitles(): # Get titles of all open images
		Image_List = WindowManager.getImageTitles()
		Image_List = [str(image) for image in Image_List]
		Prolix_Message("Opened images found: "+"\n".join(Image_List))
	else:
		Image_List=[]
		while not Image_List:
			Input_Dir_Path = Select_Folder(Default_Path = User_Desktop_Path)
			for Root, Dirs, Files in os.walk(Input_Dir_Path): # Get Files Recursively
			# Files = os.listdir(Input_Dir_Path): # Comment the line above and uncomment this line if you don"t want to get files recurcively
				for File in Files:
					if File.lower().endswith(tuple(Image_Valid_Extensions)): # Select only files ending with a Image_Valid_extensions
						Image_List.append(str(os.path.join(Root, File)))
			if not Image_List:
				Message = "No valid image files found in the selected folder."
				Advice = "Valid image file extensions are: " + ", ".join(Image_Valid_Extensions) 
				IJ.log(Message+"\n"+Advice)
				JOptionPane.showMessageDialog(None, Message+"\n"+Advice, Plugin_Name+" "+Function_Name, JOptionPane.INFORMATION_MESSAGE)
		Prolix_Message("Images found:\n"+"\n".join(Image_List))
	return Image_List

# Return InputDir_Path as a string. Used in Get_Images
def Select_Folder(Default_Path): 
	Prolix_Message("Selecting Folder...")
	Chooser = JFileChooser(Default_Path)
	Chooser.setFileSelectionMode(JFileChooser.DIRECTORIES_ONLY)
	Chooser.setDialogTitle("Choose a directory containing the images to process")
	Return_Value = Chooser.showOpenDialog(None)
	if Return_Value == JFileChooser.APPROVE_OPTION:
		InputDir_Path = Chooser.getSelectedFile().getAbsolutePath()
	else: 
		Message="Folder selection was canceled by user."
		IJ.log(Message)
		JOptionPane.showMessageDialog(None, Message, Plugin_Name+" "+Function_Name, JOptionPane.INFORMATION_MESSAGE)
		sys.exit(Message)
	Prolix_Message("Selecting Folder: " + InputDir_Path + ". Done.")
	return InputDir_Path

# Open an image using Bioformat
def Open_Image_Bioformats(File_Path):
	Prolix_Message("Importing " + str(File_Path) + " with Bioformats...")
	Bioformat_Options = ImporterOptions()
	Bioformat_Options.setId(File_Path)
	try:
		imps = BF.openImagePlus(Bioformat_Options)
		if imps and len(imps) > 0:
			Prolix_Message("Importing " + str(File_Path) + " with Bioformats. Done.")
			return imps[0]
		else:
			IJ.log("Importing with Bioformats: No Images found in the file: " + File_Path + ".")
			return None
	except Exception as Error:
		Prolix_Message("Importing with Bioformats: Error opening file" + str(Error) + ".")
		return None

# Generate a Unique filepath Directory\Basename_Suffix-001.Extension
def Generate_Unique_Filepath(Directory, Basename, Suffix, Extension):
	Prolix_Message("Generating Unique Filepath for: " + str(Basename) + "...")
	File_Counter = 1
	while True:
		Filename = "{}_{}-{:03d}{}".format(Basename, Suffix, File_Counter, Extension)
		Filepath = os.path.join(Directory, Filename)
		if not os.path.exists(Filepath):
			Prolix_Message("Generating Unique Filepath for: " + str(Basename) + ". Done.")
			return Filepath
		File_Counter += 1

# Match the Image Space Unit to a defined Standard Space Unit: m, cm, mm, micronSymbo+"m", nm
def Normalize_Space_Unit(Space_Unit):
	Prolix_Message("Standardizing space unit: " + str(Space_Unit) + "...")
	Space_Unit_Std = Space_Unit_Conversion_Dictionary.get(Space_Unit.lower(), "pixels")
	Prolix_Message("Standardizing space unit from " + str(Space_Unit) + " to " + str(Space_Unit_Std) + ".")
	return Space_Unit_Std


# Get Image Information. Works only on files written on the disk
# Return Image_Info a dictionnary including all image information
# This function also Normalize the Space Unit without writing it to the file
def Get_Image_Info(imp):
	Image_Name=imp.getTitle()
	Prolix_Message("Getting Image Info for: " + Image_Name + "...")
	File_Info = imp.getOriginalFileInfo()
	if File_Info is not None and File_Info.directory is not None:
		Filename = File_Info.fileName
		Input_Dir = File_Info.directory
		Input_File_Path = os.path.join(Input_Dir, Filename)
	else:
		Filename = "Unsaved Image"
		Input_Dir = "N/A"
		Input_File_Path = "N/A"
	Basename, Extension = os.path.splitext(Filename)
	Width = imp.getWidth()
	Height = imp.getHeight()
	Nb_Channels = imp.getNChannels()
	Nb_Slices = imp.getNSlices()
	Nb_Timepoints = imp.getNFrames()
	Bit_Depth = imp.getBitDepth()
	Current_Channel = imp.getChannel()
	Current_Slice = imp.getSlice()
	Current_Frame = imp.getFrame()
	Calibration = imp.getCalibration()
	Pixel_Width = Calibration.pixelWidth
	Pixel_Height = Calibration.pixelHeight
	Pixel_Depth = Calibration.pixelDepth
	Space_Unit = Calibration.getUnit()
	Time_Unit = Calibration.getTimeUnit()
	Frame_Interval = Calibration.frameInterval
	Calibration_Status = Calibration.scaled()
	Space_Unit_Std = Normalize_Space_Unit(Space_Unit)

	# Dictionnary storing all image information
	Image_Info = {
		"Input_File_Path": str(Input_File_Path),
		"Input_Dir": str(Input_Dir),
		"Filename": str(Filename),
		"Basename": str(Basename),
		"Extension": str(Extension),
		"Image_Name": str(Image_Name),
		"Width": int(Width),
		"Height": int(Height),
		"Nb_Channels": int(Nb_Channels),
		"Nb_Slices": int(Nb_Slices),
		"Nb_Timepoints": int(Nb_Timepoints),
		"Bit_Depth": int(Bit_Depth),
		"Current_Channel": int(Current_Channel),
		"Current_Slice": int(Current_Slice),
		"Current_Frame": int(Current_Frame),
		"Calibration": Calibration,
		"Pixel_Width": float(Pixel_Width),
		"Pixel_Height": float(Pixel_Height),
		"Pixel_Depth": float(Pixel_Depth),
		"Space_Unit": Space_Unit,
		"Space_Unit_Std": Space_Unit_Std,
		"Time_Unit": str(Time_Unit),
		"Frame_Interval": float(Frame_Interval),
		"Calibration_Status": bool(Calibration_Status),
		}
	Prolix_Message("Getting Image Info for: "+Image_Name+". Done.")
	return Image_Info

# Get Image Metadata
# Return Channel_Names_Metadata (list of channel Names as strings)
# Channel_WavelengthsEM_Metadata a list of Integer
#Objective_Mag_Metadata a string
# Objective_NA_Metadata a floating
# Objective_Immersion_Metadata a string
def Get_Metadata(imp):
	Image_Name = imp.getTitle()
	Prolix_Message("Getting Metadata for: " + Image_Name + "...")
	Image_Info = Get_Image_Info(imp)
	Bioformat_Options = ImporterOptions()
	Bioformat_Options.setId(Image_Info["Input_File_Path"])
	Metadata = MetadataTools.createOMEXMLMetadata()
	Reader = ImageReader()
	Reader.setMetadataStore(Metadata)
	Reader.setId(Image_Info["Input_File_Path"])
	try:
		if Image_Info["Nb_Channels"] > 0:
			Channel_Names_Metadata = [str(Metadata.getChannelName(0, i-1)) for i in range(1, Image_Info["Nb_Channels"]+1)]
			Channel_WavelengthsEM_Metadata = []
			for i in range(1, Image_Info["Nb_Channels"]+1 ):
				WavelengthEM = Metadata.getChannelEmissionWavelength(0, i-1)
				if WavelengthEM is not None:
					# Extract numeric value from the wavelength metadata
					value_str = str(WavelengthEM)
					start = value_str.find("value[") + 6
					end = value_str.find("]", start)
					if start != -1 and end != -1:
						value = value_str[start:end]
						Channel_WavelengthsEM_Metadata.append(int(round(float(value))))
					else:
						Channel_WavelengthsEM_Metadata.append(0)
				else:
					Channel_WavelengthsEM_Metadata.append(0)
			# Check if metadata contains objective and instrument information
			if Metadata.getInstrumentCount() > 0 and Metadata.getObjectiveCount(0) > 0:
				Objective_Magnification_Metadata = str(int(Metadata.getObjectiveNominalMagnification(0,0)))+"x"
				Objective_NA_Metadata = float(Metadata.getObjectiveLensNA(0, 0))
				Objective_Immersion_Metadata = str(Metadata.getObjectiveImmersion(0, 0))
				Prolix_Message("Getting Metadata for: " + Image_Name + ". Done.")
				return Channel_Names_Metadata, Channel_WavelengthsEM_Metadata, Objective_Magnification_Metadata, Objective_NA_Metadata, Objective_Immersion_Metadata
			else:
				IJ.log(Image_Name+" does not contain metadata. Proceeding with information from Preferences...")
				return None, None, None, None
	except Exception as Error:
		IJ.log("Error retrieving metadata: " + str(Error))
		return None, None, None, None


# Main Functions to process images.
# These function ares nested as follow
# Process_Image_List To Process a list of Images. This function calls to nested functions:
	# Process_Image
		# Display_Processing_Dialog
			# Measure_Uniformity_All_Ch
				# Measure_Uniformity_Single_Ch
					# Get the Image Statistics
					# Calculate the Std_Dev
					# Calculate the Uniformity Ratio
					# Calculate the Uniformity Standard
					# Caculate the Uniformity using the 5% 95% Percentile
					# Calculate the Coeeficient of Variation
					# Bin_Image
						# Bin the Image
						# Retrieve the X and Y Coordinates of the Reference ROI
			# Measure_Uniformity_Single_Ch
	# Process_Batch_Image
		# Measure_Uniformity_All_Ch
			# Measure_Uniformity_Single_Ch

	



# Main Function. Process a list of opened images or a list of filepath
# First image is always processed with a dialog Process_Image
# Batch processing is used when required
# Return Data_All_Files a List of Data 1 per file
# Retrurn Processed_Images_List a list of processed images

def Process_Image_List(Image_List): 
	Prolix_Message("Processing Image List")
	Processed_Images_List = []
	Data_All_Files = []
	
	for Image, Image_File in enumerate(Image_List):
		# Checking Image_File is an opened image
		if isinstance(Image_File, str) and not ("/" in Image_File or "\\" in Image_File):
			imp = WindowManager.getImage(Image_File)
			Image_Window = WindowManager.getFrame(imp.getTitle())
			Image_Window.toFront()
			File_Source="Opened"
		else: # Else Image_File is a path, import it with Bioformat
			imp = Open_Image_Bioformats(Image_File)
			File_Source="Folder"
		Zoom.set(imp, 0.5);
		imp.show()
		Image_Info = Get_Image_Info(imp)
		Image_Name = Image_Info["Image_Name"]
		IJ.log("Opening " + Image_Name + ".")
		
		# Process the first image with Process_Image function showing a Dialog
		if Image == 0:
			Prolix_Message("Processing Initial Image.")
			Data_All_Files, Processed_Images_List = Process_Image(imp, Data_All_Files, Processed_Images_List, Batch_Message="") 
			IJ.log("Success processing " + Image_Name + ".")
		# For subsequent images, check if batch mode is enabled		
		else:
			Field_Uniformity_Settings_Stored = Read_Preferences(Settings_Templates_List["Field_Uniformity.Settings_Template"])
			if Field_Uniformity_Settings_Stored["Field_Uniformity.BatchMode"]:
				Prolix_Message("Processing in Batch")
				Data_All_Files, Processed_Images_List = Process_Image_Batch(imp, Data_All_Files, Processed_Images_List)
				IJ.log("Success batch processing " + Image_Name + ".")
			else:
			 	Data_All_Files, Processed_Images_List = Process_Image(imp, Data_All_Files, Processed_Images_List, Batch_Message="")
				IJ.log("Success processing " + Image_Name + ".")
		if File_Source=="Folder":
			imp.close()
	return Data_All_Files, Processed_Images_List
	
	
# Process and Image showing a Dialog
# Return Data_All_Files
# Return Processed_Images_List
# Reset Batch_Message to ""

def Process_Image(imp, Data_All_Files, Processed_Images_List, Batch_Message):
	Image_Info = Get_Image_Info(imp)
	Image_Name = Image_Info["Image_Name"]
	IJ.log("Processing: " + Image_Name + "...")
	Dialog_Counter = 0
	User_Click = None
	Test_Processing = False
	while True:
		Field_Uniformity_Settings_Stored = Read_Preferences(Settings_Templates_List["Field_Uniformity.Settings_Template"])
		Microscope_Settings_Stored = Read_Preferences(Settings_Templates_List["Microscope_Settings_Template"])
		# Display the main dialog with Metadata and results from predetection
		Field_Uniformity_User, Microscope_Settings_User, User_Click, Dialog_Counter, Test_Processing, Batch_Message = Display_Processing_Dialog(imp, Dialog_Counter, Test_Processing, Batch_Message)
		# Filtereing some Keys to be ignored
		Field_Uniformity_Settings_Stored_Filtered = {
			key: value for key, value in Field_Uniformity_Settings_Stored.items()
			if key not in [
				"Field_Uniformity.BatchMode",
				"Field_Uniformity.Save_Individual_Files",
				"Field_Uniformity.ProlixMode"
			]}

		Field_Uniformity_User_Filtered = {
			key: value for key, value in Field_Uniformity_User.items()
			if key not in [
				"Field_Uniformity.BatchMode",
				"Field_Uniformity.Save_Individual_Files",
				"Field_Uniformity.ProlixMode"
			]}
		
		# All conditions must be fulfilled to proceed
		if User_Click == "OK" and not Test_Processing and Field_Uniformity_Settings_Stored_Filtered == Field_Uniformity_User_Filtered: #and Microscope_Settings_User == Microscope_Settings_Stored:
			break
		elif User_Click == "Cancel":
			Message = "Processing Image:" + Image_Name + ". User canceled operation."
			IJ.log(Message)
			JOptionPane.showMessageDialog(None, Message, Plugin_Name+" "+Function_Name, JOptionPane.INFORMATION_MESSAGE)
			sys.exit(Message)
	Data_File = Measure_Uniformity_All_Ch(imp, Save_File = True)
	Data_All_Files.append(Data_File)
	Processed_Images_List.append(Image_Name)
	IJ.log("Processing: " + Image_Name + ". Done.")
	return Data_All_Files, Processed_Images_List



# Process Image without Dialog Check for metadata compatibility
# Return Data_All_Files, Processed_Images_List and a Batch_Message to be passed to the Dialog in case of Metadata and Settings Mismatch
def Process_Image_Batch(imp, Data_All_Files, Processed_Images_List):
	Image_Info = Get_Image_Info(imp)
	Image_Name = Image_Info["Image_Name"]
	Nb_Channels = Image_Info["Nb_Channels"]
	IJ.log("Processing in batch: " + Image_Name + "...")
	
	Field_Uniformity_Settings_Stored = Read_Preferences(Settings_Templates_List["Field_Uniformity.Settings_Template"])
	Microscope_Settings_Stored = Read_Preferences(Settings_Templates_List["Microscope_Settings_Template"])
	
	# Trying to get some metadata
	Channel_Names_Metadata, Channel_WavelengthsEM_Metadata, Objective_Mag_Metadata, Objective_NA_Metadata, Objective_Immersion_Metadata = Get_Metadata(imp)
	
	# Check for presence of metadata and compare it with stored preferences
	Batch_Message = ""
	if Channel_Names_Metadata or Channel_Names_Metadata or Objective_Mag_Metadata or Objective_NA_Metadata or Objective_Immersion_Metadata:
		if str(Objective_Mag_Metadata) != str(Microscope_Settings_Stored["Field_Uniformity.Microscope_Objective_Mag"]):
			Batch_Message = Batch_Message + "Objective Magnification is different. Metadata: " + str(Objective_Mag_Metadata) + ". Preferences: " + str(Microscope_Settings_Stored["Field_Uniformity.Microscope_Objective_Mag"]) + "."
		
		if float(Objective_NA_Metadata) != float(Microscope_Settings_Stored["Field_Uniformity.Microscope_Objective_NA"]):
			Batch_Message = Batch_Message + "Objective NA is different. Metadata: " + str(Objective_NA_Metadata) + ". Preferences: " + str(Microscope_Settings_Stored["Field_Uniformity.Microscope_Objective_NA"]) + "."
		
		if str(Objective_Immersion_Metadata) != str(Microscope_Settings_Stored["Field_Uniformity.Microscope_Objective_Immersion"]):
			Batch_Message = Batch_Message + "\n" + "Objective Immersion is different. Metadata: " + str(Objective_Immersion_Metadata) + ". Preferences: " + str(Microscope_Settings_Stored["Field_Uniformity.Microscope_Objective_Immersion"]) + "."
		
		if Nb_Channels > len(Microscope_Settings_Stored["Field_Uniformity.Microscope_Channel_Names"]):
			Batch_Message = Batch_Message + "\n" + "Nb of Channels do not match. Image: " + str(Nb_Channels) + ". Preferences: " + str(len(Microscope_Settings_Stored["Field_Uniformity.Microscope_Channel_Names"])) + "."
		else: # Nb of Channels is sufficient check Matching values
			if Channel_Names_Metadata != Microscope_Settings_Stored["Field_Uniformity.Microscope_Channel_Names"][:Nb_Channels]:
				Batch_Message = Batch_Message + "\n" + "Channel Names are different: Metadata: " + ", ".join(Channel_Names_Metadata)+". Preferences: " + ", ".join(Microscope_Settings_Stored["Field_Uniformity.Microscope_Channel_Names"][:Nb_Channels]) + "."
			if Channel_WavelengthsEM_Metadata != Microscope_Settings_Stored["Field_Uniformity.Microscope_Channel_WavelengthsEM"][:Nb_Channels]:
				Batch_Message = Batch_Message + "\n" + "Channel Emission Wavelengths are different: Metadata: " + ", ".join(map(str, Channel_WavelengthsEM_Metadata)) + ". Preferences: " + ", ".join(map(str,Microscope_Settings_Stored["Field_Uniformity.Microscope_Channel_WavelengthsEM"][:Nb_Channels])) + "."
		if Batch_Message !="":
			Batch_Message = "Metadata different from Preferences." + "\n" + Batch_Message
			IJ.log(Batch_Message)
			Batch_Processing = "Fail"
		else:
			Batch_Processing = "Pass"
	else: # No Metadata found try with stored data
		if Nb_Channels <= len(Microscope_Settings_Stored["Field_Uniformity.Microscope_Channel_Names"]) and Nb_Channels <= len(Microscope_Settings_Stored["Field_Uniformity.Microscope_Channel_WavelengthsEM"]):
			Batch_Processing = "Pass"	
		else:
			Batch_Processing = "Fail"
	if Batch_Processing == "Pass":
		Data_File = Measure_Uniformity_All_Ch(imp, Save_File = True)
		Data_All_Files.append(Data_File)
		Processed_Images_List.append(Image_Name)
		IJ.log("Success batch processing " + Image_Name + ".")
	else:
		IJ.log("Batch processing failed for " + Image_Name + "." + "\n" + Batch_Message)
		Data_All_Files, Processed_Images_List = Process_Image(imp, Data_All_Files, Processed_Images_List, Batch_Message)
	 	IJ.log("Success processing " + Image_Name + ".")
	return Data_All_Files, Processed_Images_List





# Display a Dialog when Processing an image excepted in Batchmode
# Return Field_Uniformity_User, Microscope_Settings_User, User_Click, Dialog_Counter, Test_Processing, Batch_Message

def Display_Processing_Dialog(imp, Dialog_Counter, Test_Processing, Batch_Message):
	Image_Info = Get_Image_Info(imp)
	Image_Name = Image_Info["Image_Name"]
	Current_Channel = Image_Info["Current_Channel"]
	Prolix_Message("Displaying Processing Dialog for: " + Image_Name + "...")
	
	# Getting Metadata and Stored settings
	Channel_Names_Metadata, Channel_WavelengthsEM_Metadata, Objective_Mag_Metadata, Objective_NA_Metadata, Objective_Immersion_Metadata = Get_Metadata(imp)
	Field_Uniformity_Settings_Stored = Read_Preferences(Settings_Templates_List["Field_Uniformity.Settings_Template"])
	Microscope_Settings_Stored = Read_Preferences(Settings_Templates_List["Microscope_Settings_Template"])

	# Displaying Metadata in priority and Stored values as fall back
	Objective_Mag = Objective_Mag_Metadata if Objective_Mag_Metadata is not None and Dialog_Counter == 0 else Microscope_Settings_Stored["Field_Uniformity.Microscope_Objective_Mag"]
	Objective_NA = Objective_NA_Metadata if Objective_NA_Metadata is not None and Dialog_Counter == 0 else Microscope_Settings_Stored["Field_Uniformity.Microscope_Objective_NA"]
	Objective_Immersion = Objective_Immersion_Metadata if Objective_Immersion_Metadata and Dialog_Counter == 0 else Microscope_Settings_Stored["Field_Uniformity.Microscope_Objective_Immersion"]
	Channel_Names = Channel_Names_Metadata if Channel_Names_Metadata and Dialog_Counter == 0 else Microscope_Settings_Stored["Field_Uniformity.Microscope_Channel_Names"]
	Channel_WavelengthsEM = Channel_WavelengthsEM_Metadata if Channel_WavelengthsEM_Metadata and Dialog_Counter == 0 else Microscope_Settings_Stored["Field_Uniformity.Microscope_Channel_WavelengthsEM"]
	Channel_Names_Stored = Microscope_Settings_Stored["Field_Uniformity.Microscope_Channel_Names"]
	Channel_WavelengthsEM_Stored = Microscope_Settings_Stored["Field_Uniformity.Microscope_Channel_WavelengthsEM"]

	# Preprocessing the file before displaying the dialog
	Data_File = Measure_Uniformity_All_Ch(imp, Save_File = False)
	
	# PreProcessing the Current Channel for display purposes
	Data_Ch, Duplicated_Ch_imp = Measure_Uniformity_Single_Channel(imp, Current_Channel, Save_File = False, Display = True)
	
	
	# Create a dialog
	Processing_Dialog = NonBlockingGenericDialog(Plugin_Name+" "+Function_Name)
	Processing_Dialog.addMessage(Image_Name)
	
	# Microscope Settings section
	Processing_Dialog.addMessage("=== Microscope Settings ===")
	Processing_Dialog.addStringField("Objective Mag ({}):".format("Metadata" if Objective_Mag_Metadata and Dialog_Counter == 0 else "Pref"), Objective_Mag, 2)
	Processing_Dialog.addNumericField("Objective NA ({}):".format("Metadata" if Objective_NA_Metadata and Dialog_Counter == 0 else "Pref"), Objective_NA, 2, 4, "")
	Processing_Dialog.addRadioButtonGroup("Objective Immersion ({}):".format("Metadata" if Objective_Immersion_Metadata and Dialog_Counter == 0 else "Pref"),
						 ["Air", "Water", "Oil", "Glycerin", "Silicone"], 1, 6, Objective_Immersion)
	Processing_Dialog.addMessage("Image is "+"Calibrated" if Image_Info["Calibration_Status"] else "Uncalibrated")
	Processing_Dialog.addNumericField("Pixel Width ({0}):".format("Metadata" if Image_Info["Space_Unit_Std"] != "pixels" else "Uncalibrated"),
	Image_Info["Pixel_Width"], 4, 5, Image_Info["Space_Unit_Std"])
	Processing_Dialog.addToSameRow()
	Processing_Dialog.addStringField("Unit:", Image_Info["Space_Unit_Std"], 2)
	Processing_Dialog.addNumericField("Pixel Height ({0}):".format("Metadata" if Image_Info["Space_Unit_Std"] != "pixels" else "Uncalibrated"),
	Image_Info["Pixel_Height"], 4, 5, Image_Info["Space_Unit_Std"])
	Processing_Dialog.addToSameRow()
	Processing_Dialog.addNumericField("Bit Depth:", Image_Info["Bit_Depth"], 0, 2, "bit")
	Processing_Dialog.addNumericField("Voxel size ({0}):".format("Metadata" if Image_Info["Space_Unit_Std"] != "pixels" else "Uncalibrated"),
	Image_Info["Pixel_Depth"], 4, 5, Image_Info["Space_Unit_Std"])

	# Channel Settings section
	Processing_Dialog.addMessage("=== Channel Settings ===")
	for Channel in range (1, Image_Info["Nb_Channels"]+1):
		if Channel_Names_Metadata and len(Channel_Names_Metadata) >= Channel and Dialog_Counter == 0:
			Channel_Name = Channel_Names[Channel-1]
			Channel_Names_Source = "Metadata"
		elif len(Channel_Names_Stored) >= Channel:
			Channel_Name = Channel_Names_Stored[Channel-1]
			Channel_Names_Source = "Pref"
		else:
			Channel_Name = "Channel_{}".format(Channel)
			Channel_Names_Source = "Default"

		if Channel_WavelengthsEM_Metadata and len(Channel_WavelengthsEM_Metadata) >= Channel and Dialog_Counter == 0:
			Channel_WavelengthEM = Channel_WavelengthsEM[Channel-1]
			Channel_WavelengthsEM_Source = "Metadata"
		elif len(Channel_WavelengthsEM_Stored) >= Channel:
			Channel_WavelengthEM = Channel_WavelengthsEM_Stored[Channel-1]
			Channel_WavelengthsEM_Source = "Pref"
		else:
			Channel_WavelengthEM = NaN
			Channel_WavelengthsEM_Source = "Default"

		Processing_Dialog.addStringField("Channel {} Name ({}):".format(Channel, Channel_Names_Source), str(Channel_Name), 6)
		Processing_Dialog.addNumericField("Em Wavelength ({}):".format(Channel_WavelengthsEM_Source), int(Channel_WavelengthEM),0, 3, "nm")

	# Processing Settings
	Processing_Dialog.addMessage("=== Processing Settings ===")
	Processing_Dialog.addCheckbox("Apply Gaussian Blur", Field_Uniformity_Settings_Stored["Field_Uniformity.Gaussian_Blur"])
	Processing_Dialog.addToSameRow()
	Processing_Dialog.addCheckbox("Test Processing", Test_Processing)
	Processing_Dialog.addCheckbox("Save Individual Files", Field_Uniformity_Settings_Stored["Field_Uniformity.Save_Individual_Files"])
	Processing_Dialog.addCheckbox("Batch Mode", Field_Uniformity_Settings_Stored["Field_Uniformity.BatchMode"])
	Processing_Dialog.addToSameRow()
	Processing_Dialog.addCheckbox("Prolix Mode", Field_Uniformity_Settings_Stored["Field_Uniformity.ProlixMode"])
	Sigma_Upper_Limit = round(max(Image_Info["Width"],Image_Info["Height"])/4, -1)
	Processing_Dialog.addSlider("Gaussian Blur Sigma", 0, Sigma_Upper_Limit, Field_Uniformity_Settings_Stored["Field_Uniformity.Gaussian_Sigma"])
	Processing_Dialog.addRadioButtonGroup("Binning Method:", ["Iso-Intensity", "Iso-Density"], 1, 2, Field_Uniformity_Settings_Stored["Field_Uniformity.Binning_Method"])
	# Results from Pre Processing
	Uniformity_Per_Ch_Str = [str(float(item["Uniformity_Std"])) for item in Data_File]
	Uniformity_Per_Ch_String = ", ".join(Uniformity_Per_Ch_Str)
	Centering_Accuracy_Per_Ch_Str = [str(float(item["Centering_Accuracy"])) for item in Data_File]
	Centering_Accuracy_Per_Ch_String = ", ".join(Centering_Accuracy_Per_Ch_Str)
	Message_Uniformity = "Uniformity per channel: {}".format(Uniformity_Per_Ch_String)
	Message_Centering_Accuracy = "Centering Accuracy per channel: {}".format(Centering_Accuracy_Per_Ch_String)

	Processing_Dialog.addMessage("{}\n{}\n{}".format(Batch_Message, Message_Uniformity, Message_Centering_Accuracy))

	# Showing the Dialog
	Processing_Dialog.showDialog()
	# Closing the Preprocessed image used for display wihtout prompt
	Duplicated_Ch_imp.changes = False
	Duplicated_Ch_imp.close()
	
	# Getting info from the displayed dialog
	if Processing_Dialog.wasOKed():
		User_Click = "OK" # Flag to continue
		Microscope_Settings_User = {}
		Field_Uniformity_User = {}
		Microscope_Settings_User["Field_Uniformity.Microscope_Objective_Mag"] = Processing_Dialog.getNextString()
		Microscope_Settings_User["Field_Uniformity.Microscope_Objective_NA"] = Processing_Dialog.getNextNumber()
		Microscope_Settings_User["Field_Uniformity.Microscope_Objective_Immersion"] = Processing_Dialog.getNextRadioButton()
		Pixel_Width_User = Processing_Dialog.getNextNumber()
		Space_Unit_User = Processing_Dialog.getNextString()
		Pixel_Height_User = Processing_Dialog.getNextNumber()
		Bit_Depth_User = Processing_Dialog.getNextNumber()
		Pixel_Depth_User = Processing_Dialog.getNextNumber()

		Channel_Names_User = []
		Channel_WavelengthsEM_User = []
		for Channel in range(1, Image_Info["Nb_Channels"]+1):
			Channel_Name = Processing_Dialog.getNextString()
			Channel_WavelengthEM = Processing_Dialog.getNextNumber()
			Channel_Names_User.append(Channel_Name)
			Channel_WavelengthsEM_User.append(Channel_WavelengthEM)

		Microscope_Settings_User["Field_Uniformity.Microscope_Channel_Names"] = Channel_Names_User
		Microscope_Settings_User["Field_Uniformity.Microscope_Channel_WavelengthsEM"] = Channel_WavelengthsEM_User
		Field_Uniformity_User["Field_Uniformity.Gaussian_Blur"] = Processing_Dialog.getNextBoolean()
		Test_Processing = Processing_Dialog.getNextBoolean()
		Field_Uniformity_User["Field_Uniformity.Save_Individual_Files"] = Processing_Dialog.getNextBoolean()
		Field_Uniformity_User["Field_Uniformity.BatchMode"] = Processing_Dialog.getNextBoolean()
		Field_Uniformity_User["Field_Uniformity.ProlixMode"] = Processing_Dialog.getNextBoolean()
		Field_Uniformity_User["Field_Uniformity.Gaussian_Sigma"] = Processing_Dialog.getNextNumber()
		Field_Uniformity_User["Field_Uniformity.Binning_Method"] = Processing_Dialog.getNextRadioButton()
		Save_Preferences(Microscope_Settings_User)
		Save_Preferences(Field_Uniformity_User)

#		Prolix_Message("Updating Image Calibration for: " + Image_Name + "...")
#		Image_Calibration = imp.getCalibration()
#		Image_Calibration.pixelWidth = Pixel_Width_User if isinstance(Pixel_Width_User, (float, int)) else float(1)
#		Image_Calibration.pixelHeight = Pixel_Height_User if isinstance(Pixel_Height_User, (float, int)) else float(1)
#		Image_Calibration.pixelDepth = Pixel_Depth_User if isinstance(Pixel_Depth_User, (float, int)) else float(1)
#		Space_Unit_User_Std = Normalize_Space_Unit(Space_Unit_User)
#		Image_Calibration.setUnit(Space_Unit_User_Std)
#		imp.setCalibration(Image_Calibration)
#		Prolix_Message("Updating Image Calibration: " + Image_Name + ". Done.")
		Batch_Message=""
		Dialog_Counter += 1
	elif Processing_Dialog.wasCanceled():
		User_Click = "Cancel"
		Message = "User clicked Cancel while processing "+ Image_Name +"."
		IJ.log(Message)
		JOptionPane.showMessageDialog(None, Message, Plugin_Name+" "+Function_Name, JOptionPane.INFORMATION_MESSAGE)
		sys.exit(Message)
	Prolix_Message("Displaying Dialog for: " + Image_Name + ". Done.")
	return Field_Uniformity_User, Microscope_Settings_User, User_Click, Dialog_Counter, Test_Processing, Batch_Message


# Measure the Uniformity for all Channels
# Return a Data_File a dictionnary containing the data for all Channels for a given image
def Measure_Uniformity_All_Ch(imp, Save_File): # Run on all channels.
	Image_Info = Get_Image_Info(imp)
	Image_Name = Image_Info["Image_Name"]
	Prolix_Message("Running Uniformity on all channels for: " + Image_Name + "...")
	Current_Channel = Image_Info["Current_Channel"]
	Field_Uniformity_Settings_Stored = Read_Preferences(Settings_Templates_List["Field_Uniformity.Settings_Template"])
	#Microscope_Settings_Stored = Read_Preferences(Settings_Templates_List["Microscope_Settings_Template"])
	Data_File = [] # Store the dictionnaries containing the data for each Channel

	# Run Uniformity Single Channel and append the data
	for Channel in range(1, Image_Info["Nb_Channels"]+1):
		Data_Ch, _ = Measure_Uniformity_Single_Channel(imp, Channel, Save_File, Display = False)
		Data_File.append(Data_Ch)
	
	imp.setDisplayMode(IJ.COLOR)
	imp.setC(Current_Channel) # Channel starts from 1 to Image_Info[Nb_Channels]
	imp.updateAndDraw()

	#Define the Header and Ordered Keys has Global Variables
	global Data_File_Header
	global Data_File_Ordered_Keys
	
	
	
	Data_File_Ordered_Keys = [
	"Filename",
	"Channel_Nb",
	"Channel_Name",
	"Channel_Wavelength_EM",
	"Objective_NA",
	"Objective_Immersion",
	"Gaussian_Blur",
	"Gaussian_Sigma",
	"Binning_Method",
	"BatchMode",
	"Save_Individual_Files",
	"ProlixMode",
	"Intensity_Min",
	"Intensity_Max",
	"Intensity_Mean",
	"Intensity_Std_Dev",
	"Intensity_Median",
	"Intensity_Mode",
	"Width_Pix",
	"Height_Pix",
	"Bit_Depth",
	"Pixel_Width",
	"Pixel_Height",
	"Pixel_Depth",
	"Space_Unit",
	"Space_Unit_Std",
	"Calibration_Status",
	"Std_Dev",
	"Uniformity_Std",
	"Uniformity_Percentile",
	"CV",
	"Uniformity_CV",
	"X_Center_Pix",
	"Y_Center_Pix",
	"X_Ref_Pix",
	"Y_Ref_Pix",
	"X_Ref",
	"Y_Ref",
	"Centering_Accuracy"
	]
	
	Data_File_Header = [
	"Filename",
	"Channel Nb",
	"Channel Name",
	"Channel Wavelength EM (nm)",
	"Objective NA",
	"Objective Immersion Media",
	"Gaussian Blur Applied",
	"Gaussian Sigma",
	"Binning Method",
	"Batch Mode",
	"Save Individual CSVs",
	"Prolix Mode",
	"Image Min Intensity",
	"Image Max Intensity",
	"Image Mean Intensity",
	"Image Standard Deviation Intensity",
	"Image Median Intensity",
	"Image Mode Intensity",
	"Image Width (pixels)",
	"Image Height (pixels)",
	"Image Bit Depth",
	"Pixel Width (" + Image_Info["Space_Unit_Std"] + ")",
	"Pixel Height (" + Image_Info["Space_Unit_Std"] + ")",
	"Pixel Depth (" + Image_Info["Space_Unit_Std"] + ")",
	"Space Unit",
	"Space Unit Standard",
	"Calibration Status",",
	"Standard Deviation (GV)",
	"Uniformity Standard (%)",
	"Uniformity Percentile (%)",
	"Coefficient of Variation",
	"Uniformity CV based",
	"X Center (pixels)",
	"Y Center (pixels)",
	"X Ref (pixels)",
	"Y Ref (pixels)",
	"X Ref (" + Image_Info["Space_Unit_Std"] + ")",
	"Y Ref (" + Image_Info["Space_Unit_Std"] + ")",
	"Centering Accuracy (%)"
	]
	
	Output_Data_CSV_Path = Generate_Unique_Filepath(Output_Dir, Image_Info["Basename"], "Uniformity-Data", ".csv")
	if Save_File and Field_Uniformity_Settings_Stored["Field_Uniformity.Save_Individual_Files"]:
		#with open(Output_Data_CSV_Path, "wb") as CSVFile:
		with open(Output_Data_CSV_Path, "w") as CSV_File:
			CSV_Writer = csv.writer(CSV_File, delimiter = ",", lineterminator = "\n")
 			CSV_Writer.writerow(Data_File_Header)
 			for Data_Ch in Data_File:
 				Row = []
 				for Key in Data_File_Ordered_Keys:
 					Row.append(Data_Ch[Key])
				CSV_Writer.writerow(Row)
	Prolix_Message("Running Uniformity on all channel for: " + Image_Name + ". Done.")
	return Data_File




# Run Uniformituy on a single Channel
# Return Data_Ch a dictionnary with data for the selected Channel
def Measure_Uniformity_Single_Channel(imp, Channel, Save_File, Display):
 	Image_Info = Get_Image_Info(imp)
 	Image_Name = Image_Info["Image_Name"]
 	Prolix_Message("Running Uniformity for: "+str(Image_Name)+" Channel "+str(Channel)+".")

 	Field_Uniformity_Settings_Stored = Read_Preferences(Settings_Templates_List["Field_Uniformity.Settings_Template"])
 	Microscope_Settings_Stored = Read_Preferences(Settings_Templates_List["Microscope_Settings_Template"])

 	imp.setDisplayMode(IJ.COLOR)
	imp.setC(Channel) # Channel starts from 1 to Image_Info[Nb_Channels]
	imp.updateAndDraw()


	ip, Min, Max, Mean, Std_Dev, Median, Hist, Mode, nPixels = Get_Image_Statistics(imp)
	
	Uniformity_Std = round(Calculate_Uniformity_Std(imp), 1)
	Uniformity_Percentile = round(Calculate_Uniformity_Percentile(imp, Percentile=0.05), 1)
	CV = Calculate_CV(imp)
	if CV <= 1:
		Uniformity_CV = round(Calculate_Uniformity_CV(CV), 1)
	else:
		Uniformity_CV = "Too high"
	
	if Field_Uniformity_Settings_Stored["Field_Uniformity.Binning_Method"] == "Iso-Intensity":
		Duplicated_Ch_imp, X_Ref, Y_Ref, X_Ref_Pix, Y_Ref_Pix = Bin_Image_Iso_Intensity(imp, Channel, Display, Nb_Bins = 10, Final_Bin_Size = 25)
	else:
		Duplicated_Ch_imp, X_Ref, Y_Ref, X_Ref_Pix, Y_Ref_Pix = Bin_Image_Iso_Density(imp, Channel, Display, Nb_Bins = 10, Final_Bin_Size = 25)
	
	
	Centering_Accuracy = round(Calculate_Centering_Accuracy(imp, X_Ref_Pix, Y_Ref_Pix),1)
	
	Data_Ch={
	"Filename": Image_Info["Filename"],
	"Channel_Nb": Channel,
	"Objective_NA": Microscope_Settings_Stored["Field_Uniformity.Microscope_Objective_NA"],
	"Objective_Immersion":	Microscope_Settings_Stored["Field_Uniformity.Microscope_Objective_Immersion"],
	"Gaussian_Blur": Field_Uniformity_Settings_Stored["Field_Uniformity.Gaussian_Blur"],
	"Gaussian_Sigma": Field_Uniformity_Settings_Stored["Field_Uniformity.Gaussian_Sigma"],
	"Binning_Method": Field_Uniformity_Settings_Stored["Field_Uniformity.Binning_Method"],
	"BatchMode": Field_Uniformity_Settings_Stored["Field_Uniformity.BatchMode"],
	"Save_Individual_Files": Field_Uniformity_Settings_Stored["Field_Uniformity.Save_Individual_Files"],
	"ProlixMode": Field_Uniformity_Settings_Stored["Field_Uniformity.ProlixMode"],
	"Intensity_Min": Min,
	"Intensity_Max": Max,
	"Intensity_Mean": Mean,
	"Intensity_Std_Dev": Std_Dev,
	"Intensity_Median": Median,
	"Intensity_Mode": Mode,
	"Width_Pix": Image_Info["Width"],
	"Height_Pix": Image_Info["Height"],
	"Bit_Depth": Image_Info["Bit_Depth"],
	"Pixel_Width": Image_Info["Pixel_Width"],
	"Pixel_Height": Image_Info["Pixel_Height"],
	"Pixel_Depth": Image_Info["Pixel_Depth"],
	"Space_Unit": Image_Info["Space_Unit"],
	"Space_Unit_Std": Image_Info["Space_Unit_Std"],
	"Calibration_Status": Image_Info["Calibration_Status"],
	"Std_Dev": Std_Dev,
	"Uniformity_Std": Uniformity_Std,
	"Uniformity_Percentile": Uniformity_Percentile,
	"CV": CV,
	"Uniformity_CV": Uniformity_CV,
	"X_Center_Pix": Image_Info["Width"]/2,
	"Y_Center_Pix": Image_Info["Height"]/2,
	"X_Ref_Pix": X_Ref_Pix,
	"Y_Ref_Pix": Y_Ref_Pix,
	"X_Ref": X_Ref,
	"Y_Ref": Y_Ref,
	"Centering_Accuracy": Centering_Accuracy,
	}
	
	if Save_File:
		Data_Ch["Channel_Name"] = Microscope_Settings_Stored["Field_Uniformity.Microscope_Channel_Names"][Channel-1]
		Data_Ch["Channel_Wavelength_EM"] = Microscope_Settings_Stored["Field_Uniformity.Microscope_Channel_WavelengthsEM"][Channel-1]

	if Save_File and Field_Uniformity_Settings_Stored["Field_Uniformity.Save_Individual_Files"]:
		Output_Image_Path = Generate_Unique_Filepath(Output_Dir, Image_Info["Basename"] + "_Channel-0" + str(Channel), "Binned", ".tif")
		IJ.saveAs(Duplicated_Ch_imp, "Tiff", Output_Image_Path)
	if Display:
		Zoom.set(Duplicated_Ch_imp, 0.5);
		Duplicated_Ch_imp.show()
	if not Display:
		Duplicated_Ch_imp.changes = False
		Duplicated_Ch_imp.close()
	return Data_Ch, Duplicated_Ch_imp



# Get the statistics of the image
def Get_Image_Statistics(imp):
	Prolix_Message("Getting Image Statistics...")
	ip = imp.getProcessor()
	Stats = ip.getStatistics()
	Min = Stats.min
	Max = Stats.max
	Mean = Stats.mean
	Std_Dev = Stats.stdDev
	Median = Stats.median
	Hist = list(Stats.histogram())
	Mode = Stats.mode
	nPixels = Stats.pixelCount
	Prolix_Message("Getting Image Statistics. Done.")
	return ip, Min, Max, Mean, Std_Dev, Median, Hist, Mode, nPixels
	

# Calculate the Uniformity the same way than MetroloJ QC
def Calculate_Uniformity_Std(imp):
	Prolix_Message("Calculating Uniformity Standard...")
	ip, Min, Max, Mean, Std_Dev, Median, Hist, Mode, nPixels = Get_Image_Statistics(imp)
	Uniformity_Std = 100 * (Min / Max)
	Prolix_Message("Calculating Uniformity Standard. Done. Uniformity Standard = " + str(Uniformity_Std))
	return Uniformity_Std

# Calculate the Uniformity using the 5% 95% percentile
def Calculate_Uniformity_Percentile(imp, Percentile = 0.05):
	Prolix_Message("Calculating Uniformity 5% - 95% Percentile...")
	IJ.run(imp, "Select None", "");
	ip, Min, Max, Mean, Std_Dev, Median, Hist, Mode, nPixels = Get_Image_Statistics(imp)
	Pixels = ip.getPixels()
	Sorted_Pixels = sorted(Pixels)
	p5_Index = int(Percentile * nPixels)
	p95_Index = int((1-Percentile) * nPixels)
	Pixel_Low = Sorted_Pixels[p5_Index]
	Pixel_High = Sorted_Pixels[p95_Index]
	Uniformity_Percentile = (1 - ( float(Pixel_High - Pixel_Low) / float(Pixel_High + Pixel_Low) )) * 100
	Prolix_Message("Calculating Uniformity " + str(Percentile * 100) + "% - " + str(100 - (Percentile * 100)) + "% Percentile. Done. Uniformity Percentile = " + str(Uniformity_Percentile))
	return Uniformity_Percentile

# Calculate the Coefficient of Variation
def Calculate_CV(imp):
	Prolix_Message("Calculating Coefficient of Variation...")
	ip, Min, Max, Mean, Std_Dev, Median, Hist, Mode, nPixels = Get_Image_Statistics(imp)
	if Mean != 0:
		CV = (Std_Dev / Mean)
	else:
		CV = 0
	Prolix_Message("Calculating Coefficient of Variation. Done. CV = " + str(CV))
	return CV

# Calculate the Uniformity from the CV
def Calculate_Uniformity_CV(CV):
	Uniformity_CV = (1 - CV) * 100 # CV range from 0 to infinity but in this context it is extremely unlikely to be above 1.
	return Uniformity_CV

# Calculate the Centering Accuracy Require the X and Y coordinate of the Reference ROI
def Calculate_Centering_Accuracy(imp, X_Ref_Pix, Y_Ref_Pix):
	Prolix_Message("Calculating Centering Accuracy...")
	ip, Min, Max, Mean, Std_Dev, Median, Hist, Mode, nPixels = Get_Image_Statistics(imp)
	Width = ip.getWidth()
	Height = ip.getHeight()
	Centering_Accuracy = 100 - 100 * (2 / sqrt(Width**2 + Height**2)) * sqrt ( (X_Ref_Pix - Width/2)**2 + (Y_Ref_Pix - Height/2)**2)
	Prolix_Message("Calculating Centering Accuracy. Done. Centering Accuracy = " + str(Centering_Accuracy))
	return Centering_Accuracy

# Duplicate a Channel
def Image_Ch_Duplicator(imp, Channel, Display):
	Image_Info = Get_Image_Info(imp)
	Original_Title = Image_Info["Basename"]
	Prolix_Message("Duplicating Channel " + str(Channel) + " for " + str(Original_Title) + "...")
	New_Title = Original_Title + "_Channel-0" + str(Channel)
	Duplicated_imp = Duplicator().run(imp, Channel, Channel, 1, 1, 1, 1);
	Duplicated_imp.setTitle(New_Title)
	if Display:
		Zoom.set(Duplicated_imp, 0.5);
		Duplicated_imp.show()
	Prolix_Message("Duplicating Channel " + str(Channel) +" for " + str(Original_Title) + ". Done.")
	return Duplicated_imp # Dupicated Channel with Original Name + ChNb

# Apply Gaussian Blur with Sigma from the preferences
def Apply_Gaussian_Blur(imp, Display):
	Image_Info = Get_Image_Info(imp)
	Prolix_Message("Applying Gaussian Blur on " + str(Image_Info["Filename"]) + "...")
	Field_Uniformity_Settings_Stored = Read_Preferences(Settings_Templates_List["Field_Uniformity.Settings_Template"])
	if Field_Uniformity_Settings_Stored["Field_Uniformity.Gaussian_Blur"]:
		Sigma = Field_Uniformity_Settings_Stored["Field_Uniformity.Gaussian_Sigma"]
		ip = imp.getProcessor()
		Blur = GaussianBlur()
		Blur.blurGaussian(ip, float(Sigma))
		Prolix_Message("Applying Gaussian Blur on " + str(Image_Info["Filename"]) + ". Done.")
		if Display:
			Zoom.set(imp, 0.5);
			imp.show()
			imp.updateAndDraw()
	return None





# This is the core function of the Uniformity_Single_Channel
def Bin_Image_Iso_Intensity(imp, Channel, Display, Nb_Bins=10, Final_Bin_Size=25):
	Image_Info = Get_Image_Info(imp) # Can only be used on an image written of disk
	Prolix_Message("Binning Image with Iso-Intensity" + str(Image_Info["Filename"]) + "...")
	Height = Image_Info["Height"]
	Width = Image_Info["Width"]
	imp.setDisplayMode(IJ.COLOR)
	imp.setC(Channel) # Channel starts from 1 to Image_Info[Nb_Channels]
	imp.updateAndDraw()
	
	Field_Uniformity_Settings_Stored = Read_Preferences(Settings_Templates_List["Field_Uniformity.Settings_Template"])
	
	Duplicated_Ch_imp = Image_Ch_Duplicator(imp, Channel, Display)
	
	if Field_Uniformity_Settings_Stored["Field_Uniformity.Gaussian_Blur"]:
		Apply_Gaussian_Blur(Duplicated_Ch_imp, Display)
	
	ip, Min, Max, Mean, Std_Dev, Median, Hist, Mode, nPixels = Get_Image_Statistics(Duplicated_Ch_imp)
	
	Intensity_Range = Max - Min
	
	# Caculate the Width of the Bins based on the range of intensities
	Bin_Width = Intensity_Range / float(Nb_Bins)
	# ImageJ Macro Equation
	IJ.run(Duplicated_Ch_imp, "32-bit", "")
	Equation = "[v = " + str(Final_Bin_Size) + " + floor(((v - " + str(Min) + ") / " + str(Bin_Width) + ")) * " + str(Final_Bin_Size)+"]"
	IJ.run(Duplicated_Ch_imp, "Macro...", "code=" + Equation)
	IJ.run(Duplicated_Ch_imp, "Macro...", "code=[if(v > 250) v = 250]");
	Prolix_Message("Iso Intensity Binnig Equation = "+ str(Equation))
	#IJ.run(imp, "Math...", "operation=" + str(Equation))
	# Subtract the Minimum
	#IJ.run(Duplicated_Ch_imp, "32-bit", "")
	#IJ.run(Duplicated_Ch_imp, "Subtract...", "value=" + str(Min))
	# Divide by the Bin Width
	#IJ.run(Duplicated_Ch_imp, "Divide...", "value=" + str(Bin_Width)
	# Scale back to the Desired Bin Size
	#IJ.run(Duplicated_Ch_imp, "Multiply...", "value=" + str(Final_Bin_Size))
	#IJ.run(Duplicated_Ch_imp, "Add...", "value="+str(Final_Bin_Size))
	ImageConverter.setDoScaling(False)
	IJ.run(Duplicated_Ch_imp, "8-bit", "")
	IJ.run(Duplicated_Ch_imp, "Grays", "");
	if Display:
		Zoom.set(Duplicated_Ch_imp, 0.5);
		Duplicated_Ch_imp.show()
	
	# We have the original image imp, the Duplicated_Ch_imp (gaussian blur applied)
	# Add the overlay
	Threshold_Value_Lower = Final_Bin_Size * Nb_Bins
	Threshold_Value_Upper = 255
	
	# Duplicate the image processor to threshold on the last bin
	Thresholded_Ch_imp = Duplicated_Ch_imp.duplicate()
	IJ.setThreshold(Thresholded_Ch_imp, Threshold_Value_Lower, Threshold_Value_Upper)
	IJ.run(Thresholded_Ch_imp, "Convert to Mask", "")
	IJ.run(Thresholded_Ch_imp, "Analyze Particles...", "size=0-Infinity clear add")
	Result_Table = ResultsTable.getResultsTable()
	# Parse the result to get the largest particle
	Max_Area = 0
	Max_Area_Index = -1
	for i in range(Result_Table.getCounter()):
		Area = Result_Table.getValue("Area", i)
		if Area > Max_Area:
			Max_Area = Area
			Max_Area_Index = i
			
	if Max_Area_Index != -1:
		Roi_Manager = RoiManager.getInstance()
		Roi_Last_Bin = Roi_Manager.getRoi(Max_Area_Index)
		imp.setRoi(Roi_Last_Bin)
		Roi_Statistics = imp.getStatistics(ImageStatistics.CENTROID)
		X_Ref = Roi_Statistics.xCentroid
		Y_Ref = Roi_Statistics.yCentroid
		imp.killRoi()
		Roi_Manager.reset()
		Prolix_Message("Max_Area = " + str(Max_Area) + ".")
		Prolix_Message("Max_Area_Index = " + str(Max_Area_Index) + ".")
		Prolix_Message("X_Ref = " + str(X_Ref) + ".")
		Prolix_Message("Y_Ref = " + str(Y_Ref) + ".")
		Label_Text = "< Center here"
		
	else:
		X_Ref, Y_Ref = Width/2, Height/2
		Label_Text = "Center not found"
	
	if Image_Info["Space_Unit_Std"] != "pixels":
		X_Ref_Pix = X_Ref / Image_Info["Pixel_Width"]
		Y_Ref_Pix = Y_Ref / Image_Info["Pixel_Height"]
	else:
		X_Ref_Pix = X_Ref 
		Y_Ref_Pix = Y_Ref
	Prolix_Message("X_Ref_Pix = " + str(X_Ref_Pix) + ".")
	Prolix_Message("Y_Ref_Pix = " + str(Y_Ref_Pix) + ".")
		
	Duplicated_Ch_imp_Overlay=Overlay()
	Font_Size = max(10, min(int(min(Width, Height) * 0.03), 50))
	Font_Settings = Font("Arial", Font.BOLD, Font_Size)
	Prolix_Message("Font_Size = " + str(Font_Size))
	OffsetX = -1
	OffsetY = -int(Font_Size/2)
	Prolix_Message("OffsetX = " + str(OffsetX))
	Prolix_Message("OffsetY = " + str(OffsetY))
	Label = TextRoi(int(X_Ref_Pix+OffsetX), int(Y_Ref_Pix+OffsetY), Label_Text, Font_Settings)
	Label.setColor(Color.BLACK) # Set the font color to black
	Duplicated_Ch_imp_Overlay.add(Label)
	Thresholded_Ch_imp.changes = False
	Thresholded_Ch_imp.close()
	Duplicated_Ch_imp.setOverlay(Duplicated_Ch_imp_Overlay)
	if Display:
		Zoom.set(Duplicated_Ch_imp, 0.5);
		Duplicated_Ch_imp.show()
	Prolix_Message("Binning Image with Iso-Intensity" + str(Image_Info["Filename"]) + ". Done.")
	return Duplicated_Ch_imp, X_Ref, Y_Ref, X_Ref_Pix, Y_Ref_Pix



def Bin_Image_Iso_Density(imp, Channel, Display, Nb_Bins=10, Final_Bin_Size=25):
	Image_Info = Get_Image_Info(imp) # Can only be used on an image written of disk
	Prolix_Message("Binning Image with Iso-Density " + str(Image_Info["Filename"]) + "...")
	Height = Image_Info["Height"]
	Width = Image_Info["Width"]
	imp.setDisplayMode(IJ.COLOR)
	imp.setC(Channel) # Channel starts from 1 to Image_Info[Nb_Channels]
	imp.updateAndDraw()
	
	Field_Uniformity_Settings_Stored = Read_Preferences(Settings_Templates_List["Field_Uniformity.Settings_Template"])
	
	Duplicated_Ch_imp = Image_Ch_Duplicator(imp, Channel, Display)
	
	if Field_Uniformity_Settings_Stored["Field_Uniformity.Gaussian_Blur"]:
		Apply_Gaussian_Blur(Duplicated_Ch_imp, Display)
	
	ip, Min, Max, Mean, Std_Dev, Median, Hist, Mode, nPixels = Get_Image_Statistics(Duplicated_Ch_imp)
	Duplicated_Ch_IP = Duplicated_Ch_imp.getProcessor()
	# Get the pixel data and sort it
	Pixels = Duplicated_Ch_IP.getPixels()
	Sorted_Pixels = sorted(Pixels)
	Nb_Pixel_Per_Bin = int(nPixels / Nb_Bins)
	Prolix_Message("Nb_Pixel_Per_Bin" + str(Nb_Pixel_Per_Bin))

	Lower_Thresholds=[]
	Upper_Thresholds=[]
	for i in range(0, Nb_Bins):
		Pixel_Value_Low = Sorted_Pixels[int(i * Nb_Pixel_Per_Bin)] 
		if i == Nb_Bins - 1:
			Pixel_Value_High = Max
		else:
			Pixel_Value_High = Sorted_Pixels[int((i+1) * Nb_Pixel_Per_Bin)]
		Lower_Thresholds.append(Pixel_Value_Low)
		Upper_Thresholds.append(Pixel_Value_High)
		Prolix_Message("Pixel_Value_Low" + str(Pixel_Value_Low))
		Prolix_Message("Pixel_Value_High" + str(Pixel_Value_High))

	Roi_Manager = RoiManager.getInstance()
	if Roi_Manager is None:
		Roi_Manager = RoiManager()
	Roi_Manager.reset()
		
	# Loop through each bin
	for y in range(0, len(Lower_Thresholds)):
		Lower_Threshold_Value = Lower_Thresholds[y]
		Upper_Threshold_Value = Upper_Thresholds[y]
		Duplicated_Ch_IP.setThreshold(Lower_Threshold_Value, Upper_Threshold_Value)
		IJ.run(Duplicated_Ch_imp, "Create Selection", "")
		Roi_Manager.addRoi(Duplicated_Ch_imp.getRoi())
		Duplicated_Ch_imp.setRoi(None)
		
	IJ.run(Duplicated_Ch_imp, "8-bit", "")
	IJ.run(Duplicated_Ch_imp, "Grays", "");
	Duplicated_Ch_IP=Duplicated_Ch_imp.getProcessor()
	RM = RoiManager.getRoiManager()
		
	for Roi_Index in range(RM.getCount()):
		Roi = RM.getRoi(Roi_Index)
		New_Intensity = int ((Roi_Index + 1) * Final_Bin_Size)
		Duplicated_Ch_IP.setValue(New_Intensity)
		Duplicated_Ch_IP.fill(Roi);
		Duplicated_Ch_imp.setRoi(None)
		Prolix_Message("Roi_Index" + str(Roi_Index))
		Prolix_Message("New_Intensity" + str(New_Intensity))
	
	Roi_Manager.reset()
	Duplicated_Ch_imp.setRoi(None)
	IJ.run(Duplicated_Ch_imp, "8-bit", "");
	IJ.run(Duplicated_Ch_imp, "Grays", "");
	Duplicated_Ch_imp.updateAndDraw()

	Threshold_Value_Lower = Final_Bin_Size * (Nb_Bins)
	Threshold_Value_Upper = 255
	Prolix_Message("Threshold_Value_Lower" + str(Threshold_Value_Lower))
	
	# Duplicate the image processor to threshold on the last bin
	Duplicated_Ch_imp.setRoi(None)
	Thresholded_Ch_imp = Duplicated_Ch_imp.duplicate()
	IJ.setThreshold(Thresholded_Ch_imp, Threshold_Value_Lower, Threshold_Value_Upper)
	IJ.run(Thresholded_Ch_imp, "Convert to Mask", "")
	IJ.run(Thresholded_Ch_imp, "Analyze Particles...", "size=0-Infinity clear add")
	Result_Table = ResultsTable.getResultsTable()
	# Parse the result to get the largest particle
	Max_Area = 0
	Max_Area_Index = -1
	for i in range(Result_Table.getCounter()):
		Area = Result_Table.getValue("Area", i)
		if Area > Max_Area:
			Max_Area = Area
			Max_Area_Index = i
	Prolix_Message("Max_Area" + str(Max_Area))
	Prolix_Message("Max_Area_Index" + str(Max_Area_Index))
	
	if Max_Area_Index != -1:
		Roi_Manager = RoiManager.getInstance()
		Roi_Last_Bin = Roi_Manager.getRoi(Max_Area_Index)
		Duplicated_Ch_imp.setRoi(Roi_Last_Bin) #Or using the Original Image
		Roi_Statistics = Duplicated_Ch_imp.getStatistics(ImageStatistics.CENTROID)
		X_Ref = Roi_Statistics.xCentroid
		Y_Ref = Roi_Statistics.yCentroid
		Duplicated_Ch_imp.killRoi()
		Roi_Manager.reset()
		Label_Text = "< Center here"
	else:
		X_Ref, Y_Ref = Width/2, Height/2
		Label_Text = "Center not found"
	Prolix_Message("Label_Text" + str(Label_Text))
	
	
	if Image_Info["Space_Unit_Std"] != "pixels":
		X_Ref_Pix = X_Ref / Image_Info["Pixel_Width"]
		Y_Ref_Pix = Y_Ref / Image_Info["Pixel_Height"]
	else:
		X_Ref_Pix = X_Ref 
		Y_Ref_Pix = Y_Ref
	Prolix_Message("X_Ref_Pix" + str(X_Ref_Pix))
	Prolix_Message("Y_Ref_Pix" + str(Y_Ref_Pix))
	
	Duplicated_Ch_imp_Overlay=Overlay()
	Font_Size = max(10, min(int(min(Width, Height) * 0.03), 50))
	Font_Settings = Font("Arial", Font.BOLD, Font_Size)
	Prolix_Message("Font_Size = " + str(Font_Size))
	OffsetX = -1
	OffsetY = -int(Font_Size/2)
	Prolix_Message("OffsetX = " + str(OffsetX))
	Prolix_Message("OffsetY = " + str(OffsetY))
	Label = TextRoi(int(X_Ref_Pix+OffsetX), int(Y_Ref_Pix+OffsetY), Label_Text, Font_Settings)
	Label.setColor(Color.BLACK) # Set the font color to black
	Duplicated_Ch_imp_Overlay.add(Label)
	Thresholded_Ch_imp.changes = False
	Thresholded_Ch_imp.close()
	Duplicated_Ch_imp.setOverlay(Duplicated_Ch_imp_Overlay)
	if Display:
		Zoom.set(Duplicated_Ch_imp, 0.5);
		Duplicated_Ch_imp.show()
	Prolix_Message("Binning Image with Iso-Density " + str(Image_Info["Filename"]) + ". Done.")
	return Duplicated_Ch_imp, X_Ref, Y_Ref, X_Ref_Pix, Y_Ref_Pix


# We are done with functions... Getting to work now.
# Initializing or Resetting preferences
Initialize_Preferences(Settings_Templates_List, Reset_Preferences)

# Checking and eventually Creating Output Directory
if not os.path.exists(Output_Dir): os.makedirs(Output_Dir)

# Get some images Opened or Selected from a folder
Image_List = Get_Images()

# Process the List of Images
Data_All_Files, Processed_Images_List = Process_Image_List(Image_List) 

# Saving all data
Output_Data_CSV_Path = Generate_Unique_Filepath(Output_Dir, Function_Name + "_All-Data", "Merged", ".csv")
with open(Output_Data_CSV_Path, "w") as Merged_Output_File:
	CSV_Writer = csv.writer(Merged_Output_File, delimiter = ",", lineterminator = "\n")
	CSV_Writer.writerow(Data_File_Header) # Write the header
	for Data_File in Data_All_Files:
		for Data_Ch in Data_File:
			Row = []
			for Key in Data_File_Ordered_Keys:
				Row.append(Data_Ch[Key])
			CSV_Writer.writerow(Row)

# Data_Ch is a dictionary
# Data_File is a list of dictionaries
# Data_All_Files is a list of a list of dictionnaries

# Saving Essential Data 
Output_Simple_Data_CSV_Path = Generate_Unique_Filepath(Output_Dir, Function_Name + "_Essential-Data", "Merged", ".csv")
with open(Output_Data_CSV_Path, 'r') as Input_File:
	Reader = csv.reader(Input_File, delimiter=',', lineterminator='\n')
	Header = next(Reader)
#0.  Filename
#1.  Channel_Nb
#2.  Channel_Name
#3.  Channel_Wavelength_EM
#4.  Objective_NA
#5.  Objective_Immersion
#6.  Gaussian_Blur
#7.  Gaussian_Sigma
#8.  Binning_Method
#9.  BatchMode
#10. Save_Individual_Files
#11. ProlixMode
#12. Intensity_Min
#13. Intensity_Max
#14. Intensity_Mean
#15. Intensity_Std_Dev
#16. Intensity_Median
#17. Intensity_Mode
#18. Width_Pix
#19. Height_Pix
#20. Bit_Depth
#21. Pixel_Width
#22. Pixel_Height
#23. Pixel_Depth
#24. Space_Unit
#25. Space_Unit_Std
#26. Calibration_Status
#27. Std_Dev
#28. Uniformity_Std
#29. Uniformity_Percentile
#30. CV
#31. Uniformity_CV
#32. X_Center_Pix
#33. Y_Center_Pix
#34. X_Ref_Pix
#35. Y_Ref_Pix
#36. X_Ref
#37. Y_Ref
#38. Centering_Accuracy
	Selected_Columns = list(range(0, 3)) + [12, 13, 14, 15, 28,29,30,31,32,33,34,35,38]
	Selected_Header = [Header[i] for i in Selected_Columns]
	with open(Output_Simple_Data_CSV_Path, 'w') as Output_File:
		CSV_Writer = csv.writer(Output_File, delimiter = ',', lineterminator = '\n')
		CSV_Writer.writerow(Selected_Header) # Write the header
		for Row in Reader: # Get the data from the Saved Full data CSV File
			Selected_Row = [Row[i] for i in Selected_Columns]
			CSV_Writer.writerow(Selected_Row)
	
# Log the success message indicating the number of processed images
Message = Function_Name + " has been completed.\n" + str(len(Processed_Images_List)) + " images have been processed successfully."
Message = Message + "\n" + "Files are saved in " + str(Output_Dir)
IJ.log(Message)
JOptionPane.showMessageDialog(None, Message,Plugin_Name+" "+Function_Name, JOptionPane.INFORMATION_MESSAGE)


import java.lang.System
java.lang.System.gc() # Cleaning up my mess ;-)
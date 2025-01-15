# Function written by Nicolas Stifani nstifani@gmail.com for more info

from ij import IJ, Prefs
from ij.gui import GenericDialog
import os

# Defines Global Variables
PluginName = "QCScope"
MacroName = "Toogle Autostart"

# Set IJ Size and position
screenWidth = IJ.getScreenSize().width
screenHeight = IJ.getScreenSize().height
IJPosX = int(screenWidth * 0.1)
IJPosY = 0
IJSizeX = 570
IJSizeY = 100
Spacer = 25
IJ.getInstance().setLocation(IJPosX, IJPosY)

# Set Toolbar Size and position
ToolbarSizeX = 250
ToolbarSizeY = 200
ToolbarPosX = IJPosX + IJSizeX + Spacer
ToolbarPosY = IJPosY



# Check StartUp Macro for Content
def check_startup_macro():
	macro_folder = IJ.getDirectory("macros")
	startup_macro = "RunAtStartup.ijm"
	autostart_status = "inactive"
	write_content = "run(\"%s Toolbar\");" % PluginName
	row_autostart_status=""
	if not os.path.exists(os.path.join(macro_folder, startup_macro)):
		with open(os.path.join(macro_folder, startup_macro), 'w') as f:
			pass

	with open(os.path.join(macro_folder, startup_macro), 'r') as f:
		startup_macro_content = f.readlines()

	for n, line in enumerate(startup_macro_content):
		if write_content in line:
			autostart_status = "active"
			row_autostart_status = n
			break
	return autostart_status, startup_macro_content, row_autostart_status


# Function to display an error and propose options
def error_dialog(message_error, message_fix, error_response_array):
	dialog = GenericDialog(PluginName + " Information")
	dialog.addMessage(message_error)
	dialog.addMessage(message_fix)
	dialog.addRadioButtonGroup("", error_response_array, len(error_response_array), 1, error_response_array[0])
	dialog.setLocation(ToolbarPosX, ToolbarPosY + ToolbarSizeY + 2 * Spacer)
	dialog.showDialog()
	return dialog.getNextRadioButton()

	

# Function to display a message
def message_dialog(message):
	dialog = GenericDialog(PluginName + " Information")
	dialog.addMessage(message)
	dialog.setLocation(ToolbarPosX, ToolbarPosY + ToolbarSizeY + 2 * Spacer)
	dialog.showDialog()


# Remove StartUp Macro Content
def remove_content_startup_macro(startup_macro_content, row_autostart_status):
	macro_folder = IJ.getDirectory("macros")
	startup_macro = "RunAtStartup.ijm"
	with open(os.path.join(macro_folder, startup_macro), 'w') as f:
		for n, line in enumerate(startup_macro_content):
			if n != row_autostart_status:
				f.write(line)


# Function to clean exit
def clean_exit(message_quit):
	open_images = IJ.getImageTitles()
	for image in open_images:
		IJ.selectWindow(image)
		IJ.run("Close")
	message_dialog(message_quit)
	IJ.run("Quit")
	
	
# Main script
if __name__ == "__main__":
	autostart_status, startup_macro_content, row_autostart_status = check_startup_macro()
	message_error = "%s Autostart is currently %s." % (PluginName, autostart_status)
	message_fix = "What would you like to do?"

	if autostart_status == "active":
		error_response_array = ["Keep %s Autostart Active" % PluginName, "Remove %s Autostart" % PluginName]
	else:
		error_response_array = ["Activate %s Autostart" % PluginName, "Keep %s Autostart OFF for now" % PluginName]

	user_response = error_dialog(message_error, message_fix, error_response_array)

	if user_response == error_response_array[1]:
		if autostart_status == "active":
			remove_content_startup_macro(startup_macro_content, row_autostart_status)
		else:
			with open(os.path.join(IJ.getDirectory("macros"), "RunAtStartup.ijm"), 'a') as f:
				f.write("run(\"%s Toolbar\");\n" % PluginName)

		if error_dialog("To validate the modification ImageJ needs to restart.", "Do you want to quit ImageJ now?", ["Don't Quit", "Quit ImageJ"]) == "Quit ImageJ":
			clean_exit("The function \"%s\" will now close ImageJ." % MacroName)

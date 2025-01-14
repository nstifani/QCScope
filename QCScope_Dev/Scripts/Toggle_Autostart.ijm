// Function written by Nicolas Stifani nstifani@gmail.com for more info

// Defines Global Variables
requires("1.51n");
var PluginName="QCScope";
var MacroName="Toogle Autostart";
var FileExt="";
var MinNbFile=1;
var FolderSuffix="";
var SubDirArray=newArray("");
CellSeparator= "\t";
LineSeparator="\n";



//////////////////////////////////////////////// Header, Set Preferences, Options and Housekeeping
// Select All measurements, Invert Y, and use 9 decimals
run("Set Measurements...", "area mean standard modal min centroid center perimeter bounding fit shape feret's integrated median skewness kurtosis area_fraction stack display invert redirect=None decimal=9");
run("Line Width...", "line=1"); // Set Line width as 1
run("Input/Output...", "jpeg=100 gif=-1 file=.txt use copy_row save_column"); // Set Output as Txt and save columns and ignore row numbers
run("Point Tool...", "type=Hybrid color=yellow size=Large label show counter=0"); // Set the Point tool as yellow Medium Circle
run("Colors...", "foreground=white background=black selection=yellow"); // Set foreground and background colors Selection is yellow
run("Appearance...", "  menu=0 16-bit=Automatic"); // Change appareance of 16bit image as automatic
run("Misc...", "divide=Infinity"); // Make sure Miscellaneous Options are set correctly
run("Overlay Options...", "stroke=cyan width=2 point=Hybrid size=Large fill=none apply show"); // Overlay Options
run("Labels...", "color=White font=10 show bold"); // Labels options
call("ij.Prefs.set", "threshold.mode", 0); // Make the ImageJ preferences for threshold visualisation as Red over background

// Set IJ Size and position
IJPosX=screenWidth*0.1; // The position of ImageJ in X // Set IJ Size and position
IJPosY=screenHeight*0; // The position of ImageJ in Y at the top of the screen
IJSizeX=570; // The width of ImageJ toolbar in pixel
IJSizeY=100; // The Height of ImageJ toolbar in pixel
Spacer=25; // A spacer
DummyVariable=eval("script","IJ.getInstance().setLocation("+IJPosX+","+IJPosY+");"); // Adjust the position of the ImageJ toolbar

// Set Toolbar Size and position
ToolbarSizeX=250; // Set Toolbar Size and position
ToolbarSizeY=200; // Size of the toolbar
ToolbarPosX=IJPosX+IJSizeX+Spacer; // Position of the Toolbar is to the right of the ImageJ toolbar
ToolbarPosY=IJPosY; // Position of to the Toolbar in Y

// Position the Toolbar
if(isOpen(PluginName+" Toolbar")){selectWindow(PluginName+" Toolbar"); setLocation(ToolbarPosX,ToolbarPosY);}

// Set Threshold Window Size and Position
ThresholdSizeX=290;
ThresholdSizeY=260;
ThresholdPosX=ToolbarPosX; // The Position in X of the threshold window is below the toolbar
ThresholdPosY=ToolbarPosY+ToolbarSizeY+Spacer; // Threshold toolbar is just below the plugin toolbar
call("ij.Prefs.set", "threshold.loc", ThresholdPosX+" , "+ThresholdPosY); // Save in the preferences

// Set ROI Manager Size and Position
ROIManagerSizeX=250;
ROIManagerSizeY=300;
ROIManagerPosX=ToolbarPosX; // The Position in X of the ROI manager window
ROIManagerPosY=ToolbarPosY+ToolbarSizeY+Spacer+ThresholdSizeY+Spacer;
call("ij.Prefs.set", "manager.loc", ROIManagerPosX+" , "+ROIManagerPosY); // Save in the preferences

// Set Results Size and Position
ResultsSizeX=(screenWidth-(ToolbarPosX+ToolbarSizeX+Spacer));
ResultsSizeY=ROIManagerPosY-Spacer;
ResultsPosX=ToolbarPosX+ToolbarSizeX+Spacer;
ResultsPosY=ToolbarPosY;
call("ij.Prefs.set", "results.loc", ResultsPosX+" , "+ResultsPosY);  // Save in the preferences
call("ij.Prefs.set", "results.width", ResultsSizeX); // Save in the preferences
call("ij.Prefs.set", "results.height", ResultsSizeY); // Save in the preferences

// Set Log location
LogSizeX=(screenWidth-(ToolbarPosX+ToolbarSizeX+Spacer));
LogSizeY=ROIManagerPosY-Spacer;
LogPosX=ToolbarPosX+ToolbarSizeX+Spacer;
LogPosY=ToolbarPosY;
call("ij.Prefs.set", "log.loc", LogPosX+" , "+LogPosY); // Save in the preferences

// Set Debug location
DebugSizeX=(screenWidth-(ToolbarPosX+ToolbarSizeX+Spacer));
DebugSizeY= ROIManagerPosY-Spacer;
DebugPosX=ToolbarPosX+ToolbarSizeX+Spacer;
DebugPosY=ToolbarPosY;
call("ij.Prefs.set", "debug.loc", DebugPosX+" , "+DebugPosY); // Save in the preferences

// Set point Tool location
PointToolSizeX=250;
PointToolSizeY=300;
PointToolPosX= ToolbarPosX+ROIManagerSizeX+Spacer;
PointToolPosY= ToolbarPosY+ToolbarSizeY+Spacer+ThresholdSizeY+Spacer;

// Set Brightness and contrast location
BCSizeX=150;
BCSizeY=300;
BCPosX=PointToolPosX+PointToolSizeX+Spacer;
BCPosY=ROIManagerPosY;
call("ij.Prefs.set", "b&c.loc", BCPosX+" , "+BCPosY);  // Save in the preferences
//////////////////////////////////////////////// Header and Housekeeping




//////////////////////////////////////////////// General Functions
/////////////////////////// Function to Append to an array
function Append(ArrayI, Value) {
  ArrayJ = newArray(ArrayI.length+1);
  for (ValueI=0; ValueI<ArrayI.length; ValueI++)
  ArrayJ[ValueI] = ArrayI[ValueI];
  ArrayJ[ArrayI.length] = Value;
  return ArrayJ;
}
/////////////////////////// Function to Append to an array

/////////////////////////// Function to display a message
var MessageDialogPass;
function MessageDialog(Message){
  MessageDialogPass=0;
  Dialog.create(PluginName+" Information");
  Dialog.setInsets(0, 0, 0);
  Dialog.addMessage(Message);
  Dialog.setLocation(ToolbarPosX, ToolbarPosY+ToolbarSizeY+2*Spacer);
  ListUtilityWindows=newArray("Threshold", "Results", "ROI Manager", "B&C");
  CloseUtilityWindows(ListUtilityWindows);
  Dialog.show();
  MessageDialogPass=1;
}
/////////////////////////// Function to display a message

/////////////////////////// Function to display an error and propose to options
var ErrorDialogPass;
var UserResponseErrorDialog;
function ErrorDialog(MessageError, MessageFix, ErrorResponseArray){
  ErrorDialogPass=0;
  Dialog.create(PluginName+" Information");
  Dialog.setInsets(0, 0, 0);
  Dialog.addMessage(MessageError);
  Dialog.setInsets(0, 0, 0);
  Dialog.addMessage(MessageFix);
  Dialog.setInsets(0, 0, 0);
  Dialog.setInsets(0, 20, 0);
  Dialog.addRadioButtonGroup("", ErrorResponseArray, ErrorResponseArray.length, 1, ErrorResponseArray[0]);
  Dialog.setLocation(ToolbarPosX, ToolbarPosY+ToolbarSizeY+2*Spacer);
  ListUtilityWindows=newArray("Threshold", "Results", "ROI Manager", "B&C");
  CloseUtilityWindows(ListUtilityWindows);
  Dialog.show();
  UserResponseErrorDialog=Dialog.getRadioButton();
  return UserResponseErrorDialog;
}
/////////////////////////// Function to display an error and propose to options


/////////////////////////// Function Close and CleanUp Function
function CloseAndCleanUp(PluginName, FileI, NbFile, FileExt, InputDirName, OutputDirName){
  ListImages=getList("image.titles");
  for(n=0; n<ListImages.length; n++){ImageN=ListImages[n]; selectWindow(ImageN); run("Close");} // Close open Images
  ListUtilityWindows=newArray("Threshold", "Results", "ROI Manager", "B&C");
  CloseUtilityWindows(ListUtilityWindows);
  beep();
  // Closing Dialog Box
  Dialog.create(PluginName+" Information");
  Dialog.setInsets(0, 0, 0);
  Dialog.addMessage(FileI+" of "+ NbFile+" "+ FileExt+ " file(s) in the folder:\n\""+InputDirName+"\"\nhave been processed successfully.");
  Dialog.setInsets(0, 0, 0);
  Dialog.addMessage("Files are saved in the following folder:\n\""+OutputDirName+"\".");
  Dialog.setInsets(0, 0, 0);
  Dialog.setLocation(ToolbarPosX, ToolbarPosY+ToolbarSizeY+2*Spacer);
  Dialog.show();
}
/////////////////////////// Function Close and CleanUp Function

/////////////////////////// CleanExit Function
function CleanExit(MessageQuit){
  ListImages=getList("image.titles");
  for(n=0; n<ListImages.length; n++){ImageN=ListImages[n]; selectWindow(ImageN); run("Close");} // Close open Images
  ListUtilityWindows=newArray("Threshold", "Results", "ROI Manager", "B&C");
  CloseUtilityWindows(ListUtilityWindows);
  beep();
  Dialog.create(PluginName+" Information");
  Dialog.setInsets(0, 0, 0);
  Dialog.addMessage(MessageQuit);
  Dialog.setInsets(0, 0, 0);
  Dialog.setLocation(ToolbarPosX, ToolbarPosY+ToolbarSizeY+2*Spacer);
  Dialog.show();
  exit();
}
/////////////////////////// CleanExit Function

/////////////////////////// Close UtilityWindows
function CloseUtilityWindows(ListUtilityWindows){
  // Typically  ListUtilityWindows=newArray("Threshold", "Results", "ROI Manager", "B&C");
  for(WindowI=0; WindowI<ListUtilityWindows.length; WindowI++){
    UtilityWindowI=ListUtilityWindows[WindowI];
    if(isOpen(UtilityWindowI)){
      if(UtilityWindowI=="Results"){run("Clear Results");}
      if(UtilityWindowI=="ROI Manager"){roiManager("reset");}
      selectWindow(UtilityWindowI); run("Close"); }
    }
  }
  /////////////////////////// Close UtilityWindows
  //////////////////////////////////////////////// End of General Functions



  //////////////////////////////////////////////// Specific Functions
/////////////////////////// CleanExitandQuit Function
function CleanExitandQuit(MessageQuit){
  ListImages=getList("image.titles");
  for(n=0; n<ListImages.length; n++){
    ImageN=ListImages[n];
    selectWindow(ImageN);    run("Close");
  }
  ListUtilityWindows=newArray("Threshold", "Results", "ROI Manager", "B&C");
  CloseUtilityWindows(ListUtilityWindows);
  beep();
  Dialog.create(PluginName+" Information");
  Dialog.setInsets(0, 0, 0);
  Dialog.addMessage(MessageQuit);
  Dialog.setInsets(0, 0, 0);
  Dialog.setLocation(ToolbarPosX, ToolbarPosY+ToolbarSizeY+2*Spacer);
  Dialog.show();
  run("Quit");
}
/////////////////////////// CleanExitandQuit Function



/////////////////////////// Check StartUp Macro for Content
var MacroFolder=eval("script", "IJ.getDirectory(\"macros\");");// Get Macro Folder
var StartUpMarcro="RunAtStartup.ijm";// Get StartUp Macro Name
var AutostartStatus="inactive"; // Set autostart status
var WriteContent = "run\(\""+PluginName+" Toolbar\"\)\;"; // Content to check in the startup macro
var MatchContent = "run\\(\""+PluginName+" Toolbar\"\\)\\;";
var RowAutostartStatus=""; // Row at which the autostart status has changed
var StartUpMacroContentArray;

function CheckStartUpMacro() {
  // If the RunAtStartup does not exist create an new one
  if (!File.exists(MacroFolder+StartUpMarcro)){
    TempStartUpMacro=File.open(MacroFolder+StartUpMarcro);
    File.close(TempStartUpMacro);
  } // end of create an empty RunAtStartUp if it does not yet exist

  // Open StartUpMacro Content
  StartUpMacroContent=File.openAsString(MacroFolder+StartUpMarcro);
  // Create an Array
  StartUpMacroContentArray=split(StartUpMacroContent, "\n");

  // Screen the Content of Startup and if matches change the status to active
  for (n=0; n<StartUpMacroContentArray.length; n++){

    if(matches(StartUpMacroContentArray[n], MatchContent)==1){
      AutostartStatus="active";
      RowAutostartStatus=n;
      n=StartUpMacroContentArray.length-1; // skip the screen
    }// end of if
  } // end of for
}
/////////////////////////// Check StartUp Macro for Content



/////////////////////////// Remove StartUp Macro Content
function RemoveContentStartUpMacro(StartUpMacroContentArray, RowAutostartStatus) {
  if (File.exists(MacroFolder+StartUpMarcro)==1){
     TempStartUpMacro=File.delete(MacroFolder+StartUpMarcro);
   }
  TempStartUpMacro=File.open(MacroFolder+StartUpMarcro);
  File.close(TempStartUpMacro);
  for (n=0; n<StartUpMacroContentArray.length; n++){
    if(n==RowAutostartStatus){
      n++;
    } else {
      File.append(StartUpMacroContentArray[n],MacroFolder+StartUpMarcro);
    }
  }
}
/////////////////////////// Remove StartUp Macro Content
//////////////////////////////////////////////// Specific Functions



//////////////////////////////////////////////// Macro starts here
// Check the StartUpMacro
CheckStartUpMacro();

// Prompt User to change the autostart status
MessageError=PluginName+" Autostart is currently " +AutostartStatus+".";
MessageFix="What would you like to do?";
// Response Array is different depending on the status
if(AutostartStatus=="active"){
  ErrorResponseArray=newArray("Keep "+PluginName+" Autostart Active", "Remove "+PluginName+" Autostart");
} else if (AutostartStatus=="inactive"){
  ErrorResponseArray=newArray("Activate "+PluginName+" Autostart", "Keep "+PluginName+" Autostart OFF for now");
}
// Display the prompt
UserResponseErrorDialog=ErrorDialog(MessageError, MessageFix, ErrorResponseArray);

// Apply user responses
if (UserResponseErrorDialog=="Keep "+PluginName+" Autostart Active" || UserResponseErrorDialog=="Keep "+PluginName+" Autostart OFF for now"){
  // do nothing
}else { // do something
  if (UserResponseErrorDialog=="Remove "+PluginName+" Autostart"){ // If user want to remove the autostart
    RemoveContentStartUpMacro(StartUpMacroContentArray, RowAutostartStatus);
  }else if (UserResponseErrorDialog=="Activate "+PluginName+" Autostart"){ // Activate the autostart
    File.append(WriteContent,MacroFolder+StartUpMarcro);
    if (!isOpen(PluginName+" Toolbar")){ // Open up the toolbar
      run(PluginName+" Toolbar");
      selectWindow(PluginName+" Toolbar");
      setLocation(ToolbarPosX,ToolbarPosY);
    } // end of if toolbar is not present yet
  } // end of activate

  /// Prompt for restart if modification is done
  MessageError="To validate the modification ImageJ needs to restart.";
  MessageFix="Do you want to quit ImageJ now?";
  MessageQuit="The function \""+ MacroName+"\" will now close ImageJ.";
  ErrorResponseArray=newArray("Don't Quit", "Quit ImageJ");
  UserResponseErrorDialog=ErrorDialog(MessageError, MessageFix, ErrorResponseArray);
  if(UserResponseErrorDialog==ErrorResponseArray[ErrorResponseArray.length-1]){
    CleanExitandQuit(MessageQuit);
  }// end of user response
}// end of if modification is done
//////////////////////////////////////////////// Macro ends here

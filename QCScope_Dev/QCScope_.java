import ij.*;
import ij.process.*;
import ij.gui.*;
import ij.plugin.*;
import ij.text.TextWindow;
import ij.io.Opener;
import java.awt.*;
import java.io.*;
import java.net.*;
import java.awt.image.IndexColorModel;
import org.python.util.PythonInterpreter;
import org.python.core.*;
import java.io.InputStreamReader;
import java.io.BufferedReader;
import java.nio.charset.StandardCharsets;

public class QCScope_ implements PlugIn {
    String pathInJar = "/Scripts/";
    static boolean showArgs = true;

    public void run(String arg) {
        String msg = "";
        if (arg.equals("Field Uniformity")) {
            Uniformity(); return;
        }
        else if (arg.equals("Ch Alignment")) {
            Ch_Alignment(); return;
        }
        else if (arg.equals("Toggle Autostart")) {
            Toggle_Autostart(); return;
        }
    }

    public void Uniformity() {
        String scriptPath = pathInJar + "Field_Uniformity.py";
        if (!scriptPath.isEmpty()) {
            // Run the script using Jython
            runPythonScript(scriptPath);
        }
    }

    public void Ch_Alignment() {
        String scriptPath = pathInJar + "Ch_Alignment.py";
        if (!scriptPath.isEmpty()) {
            // Run the script using Jython
            runPythonScript(scriptPath);
        }
    }

public void Toggle_Autostart() {
    // Load the macro from the JAR file
    String macroPath = pathInJar + "Toggle_Autostart.ijm";
    InputStream inputStream = getClass().getResourceAsStream(macroPath);
    if (inputStream == null) {
        IJ.error("Error: Macro not found in JAR file: " + macroPath);
        return;
    }

    try (BufferedReader reader = new BufferedReader(new InputStreamReader(inputStream))) {
        StringBuilder macroContent = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) {
            macroContent.append(line).append("\n");
        }

        // Execute the macro content using IJ.runMacro
        IJ.runMacro(macroContent.toString());
    } catch (IOException e) {
        IJ.error("Error reading macro: " + e.getMessage());
    }
}

public void runPythonScript(String ScriptPath) {
    InputStream inputStream = getClass().getResourceAsStream(ScriptPath);
    if (inputStream == null) {
        IJ.error("Error: Script not found in JAR file: " + ScriptPath);
        return;
    }

    PythonInterpreter interpreter = new PythonInterpreter();
    try (BufferedReader reader = new BufferedReader(new InputStreamReader(inputStream, StandardCharsets.UTF_8))) {
        StringBuilder scriptContent = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) {
            scriptContent.append(line).append("\n");
        }

        // Reload sys module to access setdefaultencoding (for Python 2)
        interpreter.exec("import sys");
        interpreter.exec("reload(sys)");  // Reload sys module to make setdefaultencoding available
        interpreter.exec("sys.setdefaultencoding('utf-8')");  // Set the default encoding to UTF-8

        // Execute the script content
        interpreter.exec(scriptContent.toString());
    } catch (Exception e) {
        IJ.error("Error running the Python script: " + e.getMessage());
    }
}



}

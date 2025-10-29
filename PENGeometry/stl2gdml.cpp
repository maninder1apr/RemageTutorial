#include "G4TessellatedSolid.hh"
#include "G4TriangularFacet.hh"
#include "G4Material.hh"
#include "G4Element.hh"
#include "G4LogicalVolume.hh"
#include "G4GDMLParser.hh"
#include "G4SystemOfUnits.hh"

#include <fstream>
#include <sstream>
#include <vector>
#include <string>

int main(int argc, char** argv) {
    if (argc != 3) {
        G4cerr << "Usage: " << argv[0] << " input.stl output.gdml" << G4endl;
        return 1;
    }

    std::string stl_file = argv[1];
    std::string gdml_file = argv[2];

    // -----------------------------
    // PEN Material
    // -----------------------------
    G4Element* C = new G4Element("Carbon", "C", 6., 12.01*g/mole);
    G4Element* H = new G4Element("Hydrogen", "H", 1., 1.008*g/mole);
    G4Element* O = new G4Element("Oxygen", "O", 8., 16.00*g/mole);

    G4Material* PEN = new G4Material("PEN", 1.3*g/cm3, 3);
    PEN->AddElement(C, 14);
    PEN->AddElement(H, 10);
    PEN->AddElement(O, 4);

    // -----------------------------
    // Read STL (ASCII only) and create G4TessellatedSolid
    // -----------------------------
    G4TessellatedSolid* solidPEN = new G4TessellatedSolid("PEN_stl");

    std::ifstream infile(stl_file);
    if (!infile) {
        G4cerr << "Cannot open STL file: " << stl_file << G4endl;
        return 1;
    }

    std::string line;
    std::vector<G4ThreeVector> vertices;
    while (std::getline(infile, line)) {
        std::istringstream iss(line);
        std::string word;
        iss >> word;
        if (word == "vertex") {
            double x, y, z;
            iss >> x >> y >> z;
            vertices.emplace_back(x*mm, y*mm, z*mm);
            if (vertices.size() == 3) {
                solidPEN->AddFacet(new G4TriangularFacet(vertices[0], vertices[1], vertices[2], ABSOLUTE));
                vertices.clear();
            }
        }
    }
    solidPEN->SetSolidClosed(true);

    // -----------------------------
    // Logical volume (no world)
    // -----------------------------
    G4LogicalVolume* logPEN = new G4LogicalVolume(solidPEN, PEN, "PEN_stl_lv");

    // -----------------------------
    // Write GDML
    // -----------------------------
    G4GDMLParser parser;
    parser.Write(gdml_file, logPEN, true, true);

    G4cout << "[OK] STL file converted to GDML as PEN_stl_lv: " << gdml_file << G4endl;

    return 0;
}

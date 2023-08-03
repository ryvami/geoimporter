import logging
import os
import re
import tkinter as tk
import warnings
from tkinter import ttk
from typing import List

import sqlalchemy as sa
import sqlalchemy.exc
from dotenv import load_dotenv
from geo.Geoserver import Geoserver
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import declarative_base

from components.labeled_entry import LabeledEntry
from components.listboxbutton_entry import ListBoxandButtons
from geoserver_rest import upload_postgis, upload_raster, upload_shapefile

load_dotenv()
__shapefile__ = "SHAPEFILE"
__raster__ = "RASTER"


class GeoImporter(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        tab_control = ttk.Notebook(root)

        # initiate the tkinter frame to hold widgets
        import_frame = ttk.Frame(tab_control, padding="3 3 12 12")
        delete_frame = ttk.Frame(tab_control, padding="3 3 12 12")
        tab_control.add(import_frame, text="Import")
        tab_control.add(delete_frame, text="Delete")
        tab_control.grid(column=0, row=0)
        root.title("Geoimporter")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        self.geo_host = tk.StringVar(value=os.getenv("GEOSERVER"))
        self.geo_user = tk.StringVar(value=os.getenv("GEOSERVER_USER"))
        self.geo_pass = tk.StringVar(value=os.getenv("GEOSERVER_PASS"))
        self.connected = tk.StringVar()
        self.workspace = tk.StringVar(value=os.getenv("GEOSERVER_WORKSPACE"))
        self.tiff_files = []
        self.tiff_comp = tk.StringVar()
        self.pg_user = tk.StringVar(value=os.getenv("PG_USER"))
        self.pg_pass = tk.StringVar(value=os.getenv("PG_PASS"))
        self.pg_host = tk.StringVar(value=os.getenv("PG_HOST"))
        self.pg_port = tk.StringVar(value=os.getenv("PG_PORT"))
        self.pg_database = tk.StringVar(value=os.getenv("PG_DATABASE"))
        self.shp_files = []
        self.shp_comp = tk.StringVar()
        self.storename = tk.StringVar(value=os.getenv("STORENAME"))
        self.engine: Engine = sa.create_engine(
            "postgresql://test:testpassword@localhost:5432/data"
        )
        self.dbconnected = tk.StringVar()
        self.search_layername = tk.StringVar()
        self.search_tablename = tk.StringVar()
        self.layers = []
        self.table_names = []
        self.filtered_layers = self.layers
        self.filtered_tables = self.table_names

        host_label = LabeledEntry(
            import_frame, label_text="URL:", entry_text=self.geo_host
        )
        username_label = LabeledEntry(
            import_frame, label_text="Username:", entry_text=self.geo_user
        )
        password_label = LabeledEntry(
            import_frame,
            label_text="Password:",
            entry_text=self.geo_pass,
            show="*",
            button_label="Connect",
            button_func=self.geoconnect,
        )
        geo_connect_label = tk.Label(import_frame, textvariable=self.connected)
        workspace_label = LabeledEntry(
            import_frame, label_text="Workspace:", entry_text=self.workspace
        )
        rasterpath_label = ListBoxandButtons(
            import_frame,
            label_text="Raster Path:",
            type=__raster__,
            import_files=self.tiff_files,
            import_func=self.tiff_import,
        )
        pguser_label = LabeledEntry(
            import_frame, label_text="PG User:", entry_text=self.pg_user
        )
        pgpass_label = LabeledEntry(
            import_frame, label_text="PG Pass:", entry_text=self.pg_pass, show="*"
        )
        pghost_label = LabeledEntry(
            import_frame, label_text="PG Host:", entry_text=self.pg_host
        )
        pgport_label = LabeledEntry(import_frame, "Port:", entry_text=self.pg_port)
        pgdb_label = LabeledEntry(import_frame, "PG DB:", entry_text=self.pg_database)
        pgstore_label = LabeledEntry(
            import_frame,
            label_text="Storename:",
            entry_text=self.storename,
            button_label="Connect",
            button_func=self.pg_connect,
        )
        shape_listbox = ListBoxandButtons(
            import_frame,
            label_text="Shapefile Path:",
            type=__shapefile__,
            import_files=self.shp_files,
            import_func=self.shpimport,
        )
        dbconnected_label = tk.Label(import_frame, textvariable=self.dbconnected)
        shp_comp_label = tk.Label(import_frame, textvariable=self.shp_comp)

        ### Delete tab
        tk.Label(delete_frame, width=12, text="Layers:").grid(column=0, row=1)
        tk.Entry(delete_frame, width=50, textvariable=self.search_layername).grid(
            column=1, row=1
        )
        self.layer_listbox = tk.Listbox(delete_frame, width=50, selectmode=tk.MULTIPLE)
        ttk.Button(
            delete_frame,
            text="search",
            command=lambda: search_item(
                self, pattern=self.search_layername.get(), listbox_type=__raster__
            ),
        ).grid(column=2, row=1)
        self.layer_listbox.grid(column=1, row=2)
        tk.Button(
            delete_frame,
            text="Delete",
            command=lambda: delete_layer(
                self, indexes=self.layer_listbox.curselection()
            ),
        ).grid(column=2, row=2)

        def search_item(self, pattern: str, listbox_type: str):
            if listbox_type is __shapefile__:
                self.filtered_tables = [
                    table for table in self.table_names if re.search(pattern, table)
                ]
                self.table_listbox.delete(0, tk.END)
                self.populate_listbox(
                    listbox=self.table_listbox, layers=self.filtered_tables
                )
            else:
                self.filtered_layers = [
                    layer for layer in self.layers if re.search(pattern, layer)
                ]
                self.layer_listbox.delete(0, tk.END)
                self.populate_listbox(
                    listbox=self.layer_listbox, layers=self.filtered_layers
                )

        def delete_layer(self, indexes):
            for i in indexes:
                print("Deleting " + self.filtered_layers[i])
                print(
                    self.geo.delete_layer(
                        layer_name=self.filtered_layers[i],
                        workspace=self.workspace.get(),
                    )
                )
                self.layers.remove(self.filtered_layers[i])
            self.layer_listbox.delete(0, tk.END)
            self.populate_listbox(listbox=self.layer_listbox, layers=self.layers)

        tk.Label(delete_frame, width=12, text="Tables:").grid(column=0, row=3)
        tk.Entry(delete_frame, width=50, textvariable=self.search_tablename).grid(
            column=1, row=3
        )
        ttk.Button(
            delete_frame,
            text="search",
            command=lambda: search_item(
                self, pattern=self.search_tablename.get(), listbox_type=__shapefile__
            ),
        ).grid(column=2, row=3)
        self.table_listbox = tk.Listbox(delete_frame, width=50, selectmode=tk.MULTIPLE)
        self.table_listbox.grid(column=1, row=4)
        tk.Button(
            delete_frame,
            text="Delete",
            command=lambda: delete_table(self, self.table_listbox.curselection()),
        ).grid(column=2, row=4)

        def delete_table(self, table_arr):
            for i in table_arr:
                print("Deleting " + self.filtered_tables[i])
                print(drop_table(self, self.filtered_tables[i]))
                self.table_names.remove(self.filtered_tables[i])
            self.table_listbox.delete(0, tk.END)
            self.populate_listbox(listbox=self.table_listbox, layers=self.table_names)

        def drop_table(self, table_name):
            base = declarative_base()
            metadata = sa.MetaData()
            warnings.filterwarnings("ignore", category=sqlalchemy.exc.SAWarning)
            metadata.reflect(bind=self.engine)
            table = metadata.tables[table_name]
            if table is not None:
                base.metadata.drop_all(self.engine, [table], checkfirst=True)

        # geoserver hostname field
        host_label.grid(column=0, row=1)

        # geoserver username field
        username_label.grid(column=0, row=2)

        # geoserver password field
        password_label.grid(column=0, row=3)

        # show connected to geoserver
        geo_connect_label.grid(column=1, row=3)

        # geoserver workspace field
        workspace_label.grid(column=0, row=4)

        # tiff/raster path field
        rasterpath_label.grid(column=0, row=5)

        # POSTGIS DB user field
        pguser_label.grid(column=0, row=6)

        # POSTGIS DB password field
        pgpass_label.grid(column=0, row=7)

        # POSTGIS hostname field
        pghost_label.grid(column=0, row=8)

        # POSTGIS port field
        pgport_label.grid(column=0, row=9)

        # POSTGIS database name field
        pgdb_label.grid(column=0, row=10)

        # geoserver storename field
        pgstore_label.grid(column=0, row=11)

        # show connected to postgis db
        dbconnected_label.grid(column=1, row=11)

        # Shapefile directory path field
        shape_listbox.grid(column=0, row=12)

        # display if the shapefiles succesfully imported
        shp_comp_label.grid(column=0, row=13)

        # add x and y padding to every component
        for child in import_frame.winfo_children():
            child.grid_configure(padx=5, pady=5)

    def set_engine(self, engine):
        self.engine = engine

    def populate_listbox(self, listbox, layers):
        for item in layers:
            listbox.insert("end", item)

    def populate_tablebox(self):
        if self.engine is None:
            print("Something went wrong")
        metadata = sa.MetaData(schema="public")
        warnings.filterwarnings("ignore", category=sqlalchemy.exc.SAWarning)
        metadata.reflect(bind=self.engine)
        self.table_names = [item[7:] for item in list(metadata.tables.keys())]
        self.populate_listbox(self.table_listbox, self.table_names)

    def geoconnect(self):
        """
        Connect to the geoserver
        :return:
        """
        host = self.geo_host.get()
        username = self.geo_user.get()
        password = self.geo_pass.get()
        try:
            self.geo = Geoserver(host, username=username, password=password)
            res = self.geo.get_version()["about"]
            self.connected.set("Connected!")
            print("Connected to Geoserver")
            self.layers = [
                obj["name"]
                for obj in self.geo.get_layers(self.workspace.get())["layers"]["layer"]
            ]
            self.filtered_layers = self.layers
            self.populate_listbox(listbox=self.layer_listbox, layers=self.layers)
        except Exception:
            logging.exception("Error Connecting to Geoserver!")
            self.connected.set("Error Connection failed!")

    def create_workspace(self):
        """
        Check if the workspace exists, if not, create a workspace
        :return:
        """
        if self.geo.get_workspace(self.workspace.get()):
            print("Workspace exists")
        else:
            self.geo.create_workspace(self.workspace.get())
            print("Workspace created")

    def tiff_import(self, tiff_files: List[str]):
        """
        Create workspace if exists, and import TIFF/Raster layers on to geoserver
        :return:
        """
        print("Importing Raster Files")
        count = 0
        for file in tiff_files:
            if not os.path.isfile(file):
                self.tiff_comp.set("Error! Could not find raster file.")
            if upload_raster(
                geoserver=self.geo, filepath=file, workspace=self.workspace.get()
            ):
                count += 1
                filename = os.path.basename(file)[:-4]
                print("Successfully uploaded " + filename)
                self.layers.append(filename)
        self.tiff_comp.set("Successfully uploaded " + str(count) + " Raster Files!")

    def upload_sequence(self, file, filename):
        """
        Abstract away the nested upload sequence for easier readability.
        :return:
        """
        if not os.path.isfile(file):
            self.shp_comp.set("Error! Could not find shapefile.")
        else:
            # Uploading to POSTGIS succeeds, we can upload to Geoserver
            if upload_postgis(file, self.engine):
                if upload_shapefile(
                    geoserver=self.geo,
                    filepath=file,
                    workspace=self.workspace.get(),
                    storename=self.storename.get(),
                ):
                    print("Successfully uploaded " + filename)
                    # Update table to include new shapefile uploaded
                    self.table_names.append(filename)
                    self.layers.append(filename)
                    return True
        return False


    def shpimport(self, shp_files: List[str]):
        """
        Create workspace if doesn't exists, and import shape files
        onto PG DB and publish on geoserver
        :return:
        """
        print("Importing Shape Files")
        count = 0
        error: List[str] = []
        for file in shp_files:
            filename = os.path.basename(file[:-4])
            # Upload to file to Geoserver
            if self.upload_sequence(file, filename):
                count += 1
                error.append(filename)
        if count == len(shp_files):
            self.shp_comp.set("Successfully uploaded all Shapefiles!")
        else:
            error_layers = " ".join(error)
            self.shp_comp.set("There was an error in " + error_layers)

    def pg_connect(self):
        """
        Create featurestore and connect to PG DB
        :return: DB engine for further access/manipulation
        """
        user = self.pg_user.get()
        passw = self.pg_pass.get()
        host = self.pg_host.get()
        port = str(self.pg_port.get())
        db = self.pg_database.get()
        store = self.storename.get()
        workspace = self.workspace.get()
        engine = sa.create_engine(
            "postgresql://" + user + ":" + passw + "@" + host + ":" + port + "/" + db
        )
        store_exists = False

        # Could maybe have another function for the geoserver functions
        if self.geo.get_version():
            store_exists = self.geo.get_featurestore(
                store_name=store, workspace=workspace
            )
        else:
            print("Geoserver not connected")

        if isinstance(store_exists, str):
            self.geo.create_featurestore(
                store_name=store,
                workspace=workspace,
                db=db,
                host=host,
                port=int(port),
                pg_user=user,
                pg_password=passw,
                schema="public",
            )
            print("Feature store created!")
        else:
            print("Feature store exists!")

        try:
            engine.connect()
            print("Database Connected!")
            self.dbconnected.set("Database connected!")
        except sqlalchemy.exc.OperationalError:
            logging.exception("Error connecting to database")
            self.dbconnected.set("Failed to connect to database!")
        self.set_engine(engine)
        self.populate_tablebox()


if __name__ == "__main__":
    root = tk.Tk()
    GeoImporter(root)
    root.mainloop()

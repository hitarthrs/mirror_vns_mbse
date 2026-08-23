package FusionMaterials {
    enum def MaterialCatalog {
        doc /* Canonical material catalog for Mirror model attributes.
               Entries are synchronized from mirror_model/material.py materials_list. */
        vacuum;
        air;
        deuterium;
        aluminum_6061;
        stainless;
        beryllium;
        lead;
        LiH;
        LiD;
        rebco;
        magnet;
        tungsten;
        crispy;
        water;
        he_cooled_rafm;
        iron;
        lithium;
        cooled_tungsten;
        tungsten_carbide;
        cooled_tungsten_carbide;
        rafm_steel;
        LiPb_breeder;
        rings;
        tungsten_boride;
        WB2;
        w2b5;
        cooled_w2b5;
        TiH2;
        cooled_TiH2;
        zirconium_hydride;
        water_cooled_wc;
        copper;
        hastelloy;
        flibe;
        tantalum;
        tantalum_hydride_55;
        tantalum_hydride_30;
        cooled_rafm_steel;
        Nak_77;
        potassium;
        KCl;
        HfH2;
        titanium;
        MgO;
        MgO_HfH2;
        Fe_HfH2_WB2;
        Ti_HfH2;
        B4C;
        enriched_lithium;
        lithium_metatitanate;
        lithium_orthosilicate;
        he_cooled_tungsten_carbide;
        VV_Filler;
        concrete;
        lamno3;
        alumina;
        yttrium_oxide;
        silver;
        HT_Shield_filler;
        LT_Shield_filler;
        Magnet_Winding_Pack;
        FW_FNSF;
        BW_FNSF;
        he_manifold;
        eutectic_breeding_material;
        cooled_stainless;
        rebco_tape;
        Magnet_Winding_Pack_2;
        aluminum_1050;
        ss316ln;
        cooled_tungsten_boride;
        cooled_B4C;
        dcll_enriched_lithium_breeding_material;
        cooled_wb2;
        cooled_wb_shield;
        cooled_wb2_shield;
        cooled_w2b5_shield;
        cooled_wc_shield;
        flibe_breeding_material;
        hcpb_breeding_material;
    }

    attribute def MaterialComposition {
        doc /* Lightweight material-typing attribute for subsystem/component properties.
               Use this type anywhere a model element needs a selected catalog material. */
        attribute material : MaterialCatalog;
    }
}

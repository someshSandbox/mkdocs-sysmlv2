package Demo::Batmobile {
    part def Vehicle;

    part def Batmobile :> Vehicle {
        :>> systemIdea := "Iconic fast-response vehicle";
        part seat [2];
        part engine : BatmobileEngine;
        part body;
        interface bat2eng : PowerInterface connect battery.powerPort to engine.powerPort;
    }

    part def BatmobileEngine;
    interface def PowerInterface;

    part usage FleetVehicle : Batmobile;
}

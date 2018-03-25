using System.Collections.Generic;
using Pirates;

namespace MyBot
{
    public class TutorialBot : Pirates.IPirateBot
    {
        internal class BoardStatus
        {
            public Pirate Pirate { get; set; }
            public Treasure Treasure { get; set; }
        }

        internal class PirateTactics
        {
            public Pirate Pirate { get; set; }
            public Location FinalDestination { get; set; }
            public Location TempDestination { get; set; }
            public int Moves { get; set; }
        }

        public void DoTurn(IPirateGame game)
        {
            BoardStatus status = GetBoardStatus(game);
            PirateTactics tactics = AssignTargets(game, status);
            TakeAction(game, tactics);
        }

        private BoardStatus GetBoardStatus(IPirateGame game)
        {
            Pirate pirate = game.MyPirates()[0];
            game.Debug("pirate: " + pirate.Id);
            Treasure treasure = game.Treasures()[0];
            game.Debug("treasure: " + treasure.Id);
            return new BoardStatus() { Pirate = pirate, Treasure = treasure };
        }

        private PirateTactics AssignTargets(IPirateGame game, BoardStatus status)
        {
            PirateTactics tactics = new PirateTactics() { Pirate = status.Pirate };
            if (!tactics.Pirate.HasTreasure)
            {
                tactics.Moves = game.GetActionsPerTurn();
                tactics.FinalDestination = status.Treasure.Location;
            }
            else
            {
                tactics.Moves = 1;
                tactics.FinalDestination = status.Pirate.InitialLocation;
            }
            List<Location> possibleLocations = game.GetSailOptions(tactics.Pirate, tactics.FinalDestination, tactics.Moves);
            tactics.TempDestination = possibleLocations[0];
            return tactics;
        }

        private void TakeAction(IPirateGame game, PirateTactics tactics)
        {
            if (TryDefend(game, tactics.Pirate) == true)
            {
                return;
            }
            if (TryAttack(game, tactics.Pirate) == true)
            {
                return;
            }
            game.SetSail(tactics.Pirate, tactics.TempDestination);
        }

        private bool TryAttack(IPirateGame game, Pirate pirate)
        {
            foreach (Pirate enemy in game.EnemyPirates())
            {
                if (game.InRange(pirate, enemy))
                {
                    game.Attack(pirate, enemy);
                    return true;
                }
            }
            return false;
        }

        private bool TryDefend(IPirateGame game, Pirate pirate)
        {
            foreach (Pirate enemy in game.EnemyPirates())
            {
                if (game.InRange(pirate, enemy))
                {
                    game.Defend(pirate);
                    return true;
                }
            }
            return false;
        }
    }
}



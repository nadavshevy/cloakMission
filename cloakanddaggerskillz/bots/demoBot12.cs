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
            public Script Script { get; set; }
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
            Script script = GetAvailableScript(game);
            return new BoardStatus() { Pirate = pirate, Treasure = treasure, Script = script };
        }

        private PirateTactics AssignTargets(IPirateGame game, BoardStatus status)
        {
            PirateTactics tactics = new PirateTactics() { Pirate = status.Pirate };
            tactics.Moves = game.GetActionsPerTurn();
            if (status.Script != null)
            {
                tactics.FinalDestination = status.Script.Location;
            }
            else if (!tactics.Pirate.HasTreasure)
            {
                tactics.FinalDestination = status.Treasure.Location;
            }
            else
            {
                tactics.Moves = 1;
                tactics.FinalDestination = status.Pirate.InitialLocation;
            }
            List<Location> possibleLocations = game.GetSailOptions(tactics.Pirate, tactics.FinalDestination, tactics.Moves);
            List<Location> safeLocations = GetSafeLocations(game, possibleLocations);
			if (safeLocations.Count > 0)
			{
				tactics.TempDestination = safeLocations[0];
			}
            return tactics;
        }

        private void TakeAction(IPirateGame game, PirateTactics tactics)
        {
            if (TryBermuda(game, tactics.Pirate) == true)
            {
                return;
            }
            if (TryDefend(game, tactics.Pirate) == true)
            {
                return;
            }
            if (TryAttack(game, tactics.Pirate) == true)
            {
                return;
            }
            if (tactics.TempDestination != null)
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

        private bool TryBermuda(IPirateGame game, Pirate pirate)
        {
            if (game.GetMyBermudaZone() == null && game.GetMyScriptsNum() >= game.GetRequiredScriptsNum())
            {
                game.SummonBermudaZone(pirate);
                return true;
            }
            return false;
        }

        private List<Location> GetSafeLocations(IPirateGame game, List<Location> locations)
        {
            List<Location> safeLocations = new List<Location>();
            foreach (var loc in locations)
            {
                if (!game.InEnemyBermudaZone(loc))
                {
                    safeLocations.Add(loc);
                }
            }
            return safeLocations;
        }

        private Script GetAvailableScript(IPirateGame game)
        {
            if (game.Scripts().Count > 0)
            {
                return game.Scripts()[0];
            }
            return null;
        }
    }
}



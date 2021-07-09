import React from "react";

import { Route } from "react-router-dom";
import { AuthContext } from "../contexts";

import { Skills } from "../Pages/Skills";
import { Waitlist } from "../Pages/Waitlist";
import { Fleet, FleetRegister } from "../Pages/Fleet";
import { Xup, XupCheck } from "../Pages/Xup";
import { Pilot } from "../Pages/Pilot";
import { Search } from "../Pages/Search";
import { Home } from "../Pages/Home";
import { Guide, GuideIndex } from "../Pages/Guide";
import { Statistics } from "../Pages/Statistics";

import { BanRoutes } from "../Pages/Bans";
import { ACLRoutes } from "../Pages/ACL";
import { AuthRoutes } from "../Pages/Auth";

export function Routes() {
  const authContext = React.useContext(AuthContext);
  return (
    <>
      <Route exact path="/">
        <Home />
      </Route>
      <Route exact path="/guide">
        <GuideIndex />
      </Route>
      <Route exact path="/guide/:guideName">
        <Guide />
      </Route>
      {authContext && (
        <>
          <Route exact path="/skills">
            <Skills />
          </Route>
          <Route exact path="/fleet">
            <Fleet />
          </Route>
          <Route exact path="/fleet/register">
            <FleetRegister />
          </Route>
          <Route exact path="/xup">
            <Xup />
          </Route>
          <Route exact path="/xup/check">
            <XupCheck />
          </Route>
          <Route exact path="/pilot">
            <Pilot />
          </Route>
          <Route exact path="/search">
            <Search />
          </Route>
          <Route exact path="/waitlist">
            <Waitlist />
          </Route>
          <Route exact path="/stats">
            <Statistics />
          </Route>

          <BanRoutes />
          <ACLRoutes />
        </>
      )}

      <AuthRoutes />
    </>
  );
}

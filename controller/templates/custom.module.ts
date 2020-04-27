import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { RapydoModule } from '@rapydo/rapydo.module';
import { AuthGuard } from '@rapydo/app.auth.guard';

// import { MyComponent } from './components/mycomponent'

const routes: Routes = [
/*
  {
    path: '',
    redirectTo: '/app/myroute',
    pathMatch: 'full'
  },
  {
    path: 'app',
    redirectTo: '/app/myroute',
    pathMatch: 'full'
  },
  {
    path: 'app/myroute',
    component: MyComponent,
    canActivate: [AuthGuard],
    runGuardsAndResolvers: 'always',
  },
*/
];

@NgModule({
  imports: [
    RapydoModule,
    RouterModule.forChild(routes),
  ],
  declarations: [
    MyComponent
  ],

  providers: [],

  exports: [
    RouterModule
  ]

})
export class CustomModule {
} 
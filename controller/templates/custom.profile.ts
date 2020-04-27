import { Component, Input } from '@angular/core';

@Component({
  selector: '[my-profile-row]',
  templateUrl: 'custom.profile.html'

})
export class CustomProfileComponent {

  @Input() row: any;

  constructor() { }

}